#!/usr/bin/env python3
"""P10QU: independent, un-cancelled three-axis comparison of real M8 cuts.

All 30 q256 axis-2 references are frozen P10QR/P10QS/P10QT actual ray values.
New axes 0 and 1 have independent q128/q256 projected-critical results.
Neither their agreement nor common q256 comparator is an error certificate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from P10QU_M8_CASE5_TWO_NEW_AXES_REAL_CURVED_CRITICAL_EVENTS import PIN

LABELS=('uniform_q128','critical_t128','critical_t256')


def read(root:Path,name:str,provenance:dict):
    path=root/name
    data=path.read_bytes()
    provenance[name]=hashlib.sha256(data).hexdigest()
    return json.loads(data)


def summary(rows,mode1,mode2,denom,volume):
    differences=[(r['index'],
                  r[mode1]['gradient']-r[mode2]['gradient'],
                  r[mode1]['volume']-r[mode2]['volume']) for r in rows]
    l1=sum(abs(g) for _,g,_ in differences)
    lv=sum(abs(v) for _,_,v in differences)
    sg=sum(g for _,g,_ in differences)
    worst=sorted(differences,key=lambda x:abs(x[1]),reverse=True)[:5]
    return {'method_A':mode1,'method_B':mode2,'number_of_real_cuts':len(differences),
            'L1_gradient_m3':l1,'L1_gradient_relative_full_hybrid':l1/denom,
            'L1_volume_m3':lv,'L1_volume_relative_full_child':lv/volume,
            'signed_gradient_m3':sg,'cancellation_ratio':l1/max(abs(sg),1e-70),
            'empirical_L1_below_1e_minus_6':l1/denom<1e-6,
            'five_largest_absolute_gradient_differences':[
                {'index':idx,'absolute_gradient_m3':abs(g),
                 'signed_gradient_m3':g,'absolute_volume_m3':abs(v)} for idx,g,v in worst]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,default=Path('.'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    root=a.directory
    prov={}
    ch=read(root,'P10QO_M8_REAL_CASE5_H8_CHILDREN_QA.json',prov)
    p10qt=read(root,'P10QT_M8_CASE5_FULL30_SINGLE_AXIS_INDEPENDENT_Q256_AUDIT_QA.json',prov)
    a0=read(root,'P10QO_M8_CASE5_AXIS0_Q16_128.json',prov)
    a1=read(root,'P10QO_M8_CASE5_AXIS1_Q16_128.json',prov)
    a2=read(root,'P10QO_M8_CASE5_AXIS2_Q16_128.json',prov)
    if any(r['mesh_sha256']!=PIN or r['physical_4D_FEM_approved']
           for r in (ch,p10qt,a0,a1,a2)) or \
       [a0['axis'],a1['axis'],a2['axis']]!=[0,1,2]:
        raise ValueError('P10QU_AUDIT_BASE_INPUTS_WRONG')
    full=ch['terminals']
    indices=sorted(i for i,t in enumerate(full) if t['group'] in ('one','multi'))
    if len(indices)!=30 or sorted(p10qt['full_30_cell_indices'])!=indices:
        raise ValueError('P10QU_AUDIT_NOT_TRUE_30_CUT_SOURCE')
    refs={};previous_axis2={}
    for stage,parts in (('P10QR',2),('P10QS',4),('P10QT',4)):
        if stage=='P10QR':
            names=[f'P10QR_M8_CASE5_P2_CRITICAL_S_PART{k}_QA.json' for k in range(parts)]
        elif stage=='P10QS':
            names=[f'P10QS_M8_ALL_AZ_ONE_PART{k}_QA.json' for k in range(parts)]
        else:
            names=[f'P10QT_M8_CASE5_REMAINING8_PART{k}_QA.json' for k in range(parts)]
        for name in names:
            rep=read(root,name,prov)
            if rep['mesh_sha256']!=PIN or rep['physical_4D_FEM_approved'] or rep['axis']!=2:
                raise ValueError('P10QU_BAD_PREVIOUS_AXIS2_REFERENCE')
            for r in rep['cells']:
                idx=r['index']
                if idx in refs:raise ValueError('P10QU_DUPLICATE_AXIS2_Q256_REFERENCE')
                refs[idx]=r['q256_reference'];previous_axis2[idx]=r['segmented']
    if sorted(refs)!=indices:raise ValueError('P10QU_INCOMPLETE_AXIS2_Q256_PANEL')
    results={}
    for axis,base in ((0,a0),(1,a1)):
        data={}
        for part in range(4):
            name=f'P10QU_M8_AXIS{axis}_PART{part}_QA.json'
            report=read(root,name,prov)
            if report['mesh_sha256']!=PIN or report['physical_4D_FEM_approved'] or \
               report['axis']!=axis or report['part']!=part:
                raise ValueError('P10QU_AUDIT_NEW_AXIS_SOURCE_GUARD')
            for r in report['cells']:
                if r['index'] in data:raise ValueError('P10QU_DUPLICATE_CELL_IN_AXIS')
                data[r['index']]=r
        if sorted(data)!=indices:raise ValueError('P10QU_INCOMPLETE_AXIS_DATA')
        if sorted(r['index'] for r in base['cells'])!=indices:
            raise ValueError('P10QU_PRIOR_AXIS_UNIFORM_PANEL_CHANGED')
        results[axis]=data
    # Check the 8 P10QU preflight partitions were performed on real GL nodes.
    preflight={'outer_t_slices_checked':0,'guarded_azimuth_degree_trim_count':0,
               'max_radial_w3_w4_relative':0.,'max_azimuth_w2_relative':0.,
               'max_reconstruction_relative':0.,'max_s_intervals':0}
    for axis in (0,1):
        verified=[]
        for part in range(4):
            name=f'P10QU_M8_AXIS{axis}_PREFLIGHT_PART{part}_QA.json'
            qa=read(root,name,prov)
            if qa['mesh_sha256']!=PIN or qa['physical_4D_FEM_approved'] or \
               qa['axis']!=axis or qa['part']!=part or \
               not qa['topology_sample_checks_passed'] or \
               not qa['numerical_P4_to_P2_and_P2_to_P1_guards_passed']:
                raise ValueError('P10QU_PREFLIGHT_PART_DID_NOT_PASS')
            preflight['outer_t_slices_checked']+=qa['total_checked_outer_t_slices']
            for r in qa['cells']:
                verified.append(r['index'])
                preflight['guarded_azimuth_degree_trim_count']+=r['guarded_degree_trim_count']
                preflight['max_radial_w3_w4_relative']=max(
                    preflight['max_radial_w3_w4_relative'],r['max_radial_ray_w3_w4_relative'])
                preflight['max_azimuth_w2_relative']=max(
                    preflight['max_azimuth_w2_relative'],r['max_azimuth_ray_w2_relative'])
                preflight['max_reconstruction_relative']=max(
                    preflight['max_reconstruction_relative'],
                    r['max_radial_reconstruction_relative'],r['max_azimuth_reconstruction_relative'])
                preflight['max_s_intervals']=max(preflight['max_s_intervals'],r['max_s_segments'])
        if sorted(verified)!=indices:raise ValueError('P10QU_PREFLIGHT_30_NOT_COMPLETE')
    if preflight['outer_t_slices_checked']!=2*30*(128+256):
        raise ValueError('P10QU_TOTAL_PREFLIGHT_SLICES_WRONG')
    base_by_axis={ax:{r['index']:r['order']['128'] for r in j['cells']}
                  for ax,j in ((0,a0),(1,a1))}
    rows=[];maxfull=0.;total_points={}
    for idx in indices:
        term=full[idx]
        item={'index':idx,'group':term['group'],
              'active':[k for k,v in enumerate(term['status']) if v==0]}
        for axis in (0,1):
            r=results[axis][idx]
            if r['active']!=item['active'] or r['group']!=item['group']:
                raise ValueError('P10QU_ACTUAL_GEOMETRIC_CONSTRAINT_CHANGED')
            if max(r['full_gradient_relative_error'],r['full_volume_relative_error'])>1e-10:
                raise ValueError('P10QU_SPLIT_FULL_POLYNOMIAL_NOT_ACCURATE')
            maxfull=max(maxfull,r['full_gradient_relative_error'],r['full_volume_relative_error'])
            if any(r['critical'][n]['unresolved_topology_intervals'] for n in ('128','256')):
                raise ValueError('P10QU_TOPOLOGY_UNRESOLVED_NOT_ACCEPTED')
            if r['uniform_axis_q128']['cut_gradient_m3']!=base_by_axis[axis][idx]['cut_gradient_m3']:
                raise ValueError('P10QU_UNIFORM_BASELINE_CHANGED')
            for method,r0 in (('uniform_q128',r['uniform_axis_q128']),
                              ('critical_t128',r['critical']['128']),
                              ('critical_t256',r['critical']['256'])):
                item[f'axis{axis}_{method}']={'gradient':r0['cut_gradient_m3'],
                                             'volume':r0['cut_volume_m3']}
                total_points[f'axis{axis}_{method}']=total_points.get(f'axis{axis}_{method}',0)+r0['transverse_Gauss_points']
        for method,r0 in (('uniform_q256',refs[idx]),
                          ('critical_t128',previous_axis2[idx]['128']),
                          ('critical_t256',previous_axis2[idx]['256'])):
            item[f'axis2_{method}']={'gradient':r0['cut_gradient_m3'],
                                    'volume':r0['cut_volume_m3']}
        rows.append(item)
    denominator=abs(a2['hybrid_gradient_by_order_m3']['128'])
    volume=a2['root_physical_volume_m3']
    if not 1e-15<denominator<1e-12 or not 1e-15<volume<1e-12:
        raise ValueError('P10QU_NORMALIZATION_INVALID')
    comparisons=[]
    for axis in (0,1):
        for method in LABELS:
            comparisons.append(summary(rows,f'axis{axis}_{method}','axis2_uniform_q256',denominator,volume))
        comparisons.append(summary(rows,f'axis{axis}_critical_t128',f'axis{axis}_critical_t256',denominator,volume))
        comparisons.append(summary(rows,f'axis{axis}_critical_t128','axis2_critical_t128',denominator,volume))
        comparisons.append(summary(rows,f'axis{axis}_critical_t256','axis2_critical_t256',denominator,volume))
    for method in LABELS:
        comparisons.append(summary(rows,f'axis0_{method}',f'axis1_{method}',denominator,volume))
    comparisons.append(summary(rows,'axis2_critical_t128','axis2_uniform_q256',denominator,volume))
    comparisons.append(summary(rows,'axis2_critical_t256','axis2_uniform_q256',denominator,volume))
    prior=p10qt['group_results']['all_30']['methods']
    for new,method in zip(comparisons[-2:],('critical_s_t128','critical_s_t256')):
        old=prior[method]
        if abs(new['L1_gradient_relative_full_hybrid']-
               old['L1_gradient_relative_hybrid'])>1e-12 or \
           abs(new['L1_volume_relative_full_child']-
               old['L1_volume_relative_full_child'])>1e-12:
            raise ValueError('P10QU_INDEPENDENT_RECONSTRUCT_AXIS2_P10QT_L1_MISMATCH')
    comparisons.append(summary(rows,'axis2_critical_t128','axis2_critical_t256',denominator,volume))
    improved={}
    for axis in (0,1):
        improved[str(axis)]=sum(
            abs(r[f'axis{axis}_critical_t128']['gradient']-r['axis2_uniform_q256']['gradient'])
            < abs(r[f'axis{axis}_uniform_q128']['gradient']-r['axis2_uniform_q256']['gradient'])
            for r in rows)
    result={'stage':'P10QU','scope':'3-axis full30 numerical comparison, numerical axis2 uniform q256 is not exact truth',
            'mesh_sha256':PIN,'source_case':5,'original_element_id':5865,
            'cut_count':30,'axes':[0,1,2],'normalized_gradient_by_axis2_full_hybrid_q128_m3':denominator,
            'normalized_volume_by_original_child_m3':volume,
            'preflight':preflight,'total_new_axis_Gauss_points':total_points,
            'max_split_full_polynomial_relative_error':maxfull,
            'axis0_axis1_improved_cut_counts_vs_axis2_q256':improved,
            'comparisons':comparisons,'per_cut_absolute_values':rows,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'all_input_sha256':prov,'q256_comparator_not_exact_truth':True,
            'interpolated_coefficients_and_double_roots_not_interval_certified':True,
            'not_a_global_M8_or_43200_4D_cell_certification':True,
            'physical_4D_FEM_approved':False,'no_mesh_change_no_CAD_no_Gmsh_no_FEM':True}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    for x in comparisons:
        print(f'P10QU_AUDIT {x["method_A"]} - {x["method_B"]} '
              f'L1_g={x["L1_gradient_relative_full_hybrid"]:.8e} '
              f'L1_vol={x["L1_volume_relative_full_child"]:.8e} '
              f'pass={x["empirical_L1_below_1e_minus_6"]}',flush=True)
    print('P10QU_INDEPENDENT_THREE_AXIS_FULL30_L1_AUDIT_COMPLETE_NOT_FEM',flush=True)


if __name__=='__main__':main()
