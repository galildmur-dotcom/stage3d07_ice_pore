#!/usr/bin/env python3
"""Independent recomputation of P10QK h/q/strategy metrics from recorded nodes.

Fails closed on wrong M8, stale source provenance, missing q, false mass
partition or inconsistent L1/signed aggregation. Never authorizes physical FEM.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

PIN='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'
SOURCE=Path('P10QK_M8_HYBRID_ONE_OR_TWO_CUT_ALGOIM.cpp')
AUTO=Path('P10QK_M8_HYBRID_H_AND_Q_AUTOMIXED_QA.json')
GL=Path('P10QK_M8_HYBRID_H_AND_Q_ALWAYS_GL_QA.json')


def get(name,expected_strategy,levels):
    report=json.loads(name.read_text())
    if report['mesh_sha256']!=PIN or report['source_sha256']!=hashlib.sha256(SOURCE.read_bytes()).hexdigest() \
       or report['quadrature_strategy']!=expected_strategy or report['physical_4D_FEM_approved']:
        raise ValueError('P10QK_STALE_OR_UNPINNED_STUDY')
    if [p['min_h_one'] for p in report['partitions']]!=levels:
        raise ValueError('P10QK_INCOMPLETE_H_LEVELS')
    for part in report['partitions']:
        cuts=[t for t in part['terminals'] if 'q' in t]
        if len(cuts)!=part['group_counts']['one']+part['group_counts']['multi'] or part['worker_failures']:
            raise ValueError('P10QK_MISSING_CUT_CELLS')
        d=[t['q']['8']['cut_gradient_m3']-t['q']['6']['cut_gradient_m3'] for t in cuts]
        l1=sum(abs(v) for v in d)
        sg=sum(d)
        if not math.isclose(l1,part['q6_q8_L1_delta_m3'],rel_tol=2e-12,abs_tol=1e-28) or \
           not math.isclose(sg,part['q6_q8_signed_delta_m3'],rel_tol=2e-12,abs_tol=1e-28):
            raise ValueError('P10QK_SIGNED_L1_Q_AGGREGATION_BROKEN')
        for q in ('2','3','4','6','8'):
            val=part['exact_inside_gradient_m3']+sum(t['q'][q]['cut_gradient_m3'] for t in cuts)
            if not math.isclose(val,part['q_total_gradient_m3_by_order'][q],rel_tol=2e-12,abs_tol=1e-25):
                raise ValueError('P10QK_HYBRID_SUM_BROKEN')
        if part['mass_partition_closure']>3e-10 or \
           abs(sum(part['physical_volume_by_class_fraction'].values())-1)>3e-10:
            raise ValueError('P10QK_VOLUME_MASS_UNCLOSED')
    return report


def details(part):
    q8=part['q_total_gradient_m3_by_order']['8']
    cuts=[t for t in part['terminals'] if 'q' in t]
    allqs=[v for t in cuts for v in t['q'].values()]
    return {'h_min_one':part['min_h_one'],
            'classes':part['group_counts'],
            'class_volume_fractions':part['physical_volume_by_class_fraction'],
            'q8_total_gradient_m3':q8,
            'q6_q8_L1_absolute_m3':part['q6_q8_L1_delta_m3'],
            'q6_q8_L1_relative_to_total_q8':part['q6_q8_L1_delta_m3']/max(abs(q8),1e-25),
            'q6_q8_signed_absolute_m3':abs(part['q6_q8_signed_delta_m3']),
            'q6_q8_signed_relative_to_total_q8':abs(part['q6_q8_signed_delta_m3'])/max(abs(q8),1e-25),
            'q8_point_count':sum(t['q']['8']['points'] for t in cuts),
            'full_polynomial_fail_cells':sum(not t['analytic_full_polynomial_pass'] for t in cuts),
            'max_full_moment_relative_error':max(max(q['full_gradient_relative'],q['full_volume_relative'])
                                                    for q in allqs),
            'local_cut_q6_q8_threshold_failed_cells':len(part['local_cut_q_convergence_failed_indices']),
            'all_worker_runs_completed':not part['worker_failures']}


def main():
    auto=get(AUTO,'auto',[0,4,6,8])
    gl=get(GL,'gl',[0,8])
    ap={p['min_h_one']:p for p in auto['partitions']}
    gp={p['min_h_one']:p for p in gl['partitions']}
    comparisons=[]
    for lev in (0,8):
        aa=ap[lev]['terminals'];gg=gp[lev]['terminals']
        if len(aa)!=len(gg):raise ValueError('P10QK_DIFFERENT_H_PARTITIONS_ACROSS_STRATEGIES')
        deltas=[]
        for a,g in zip(aa,gg):
            if a['index']!=g['index'] or a['group']!=g['group'] or a['h_depth']!=g['h_depth']:
                raise ValueError('P10QK_MISMATCHED_PHYSICAL_SUBTETRA')
            if 'q' in a:
                deltas.append(g['q']['8']['cut_gradient_m3']-a['q']['8']['cut_gradient_m3'])
        gl_total=gp[lev]['q_total_gradient_m3_by_order']['8']
        comparisons.append({'h_min_one':lev,
                            'q8_strategy_L1_absolute_m3':sum(abs(d) for d in deltas),
                            'q8_strategy_signed_absolute_m3':abs(sum(deltas)),
                            'q8_strategy_L1_relative_to_total':sum(abs(d) for d in deltas)/abs(gl_total),
                            'q8_strategy_signed_relative_to_total':abs(sum(deltas))/abs(gl_total)})
    gl0=details(gp[0]);gl8=details(gp[8]);auto0=details(ap[0]);auto8=details(ap[8])
    if any(v['full_polynomial_fail_cells'] for v in (gl0,gl8)) or \
       not any(v['full_polynomial_fail_cells'] for v in (auto0,auto8)) or \
       gl8['local_cut_q6_q8_threshold_failed_cells']!=27:
        raise ValueError('P10QK_UNEXPECTED_NUMERICAL_OUTCOME_OR_FAILED_CONTROL')
    result={'stage':'P10QK','date_utc':'2026-11-28',
            'mesh_sha256':PIN,'source_cpp_sha256':auto['source_sha256'],
            'scientific_status':'GL_CORRECTS_FULL_MOMENTS_BUT_TRUE_CUT_CONVERGENCE_NOT_CERTIFIED',
            'auto_h_sweep':[details(p) for p in auto['partitions']],
            'always_gl':[gl0,gl8],
            'quadrature_strategy_signed_and_L1_deltas':comparisons,
            'always_gl_q8_signed_h0_h8_relative':abs(gl8['q8_total_gradient_m3']-
                gl0['q8_total_gradient_m3'])/abs(gl8['q8_total_gradient_m3']),
            'always_gl_h8_L1_reduction_factor_vs_h0':gl0['q6_q8_L1_absolute_m3']/
                                                   gl8['q6_q8_L1_absolute_m3'],
            'multi_two_boundary_uncertainty_bracket_m3':gp[8]['residual_multi_bernstein_enclosure_m3'],
            'floating_bernstein_bounds_not_directed_rounding':True,
            'q6_q8_difference_is_not_proven_error_bound':True,
            'all_48_physical_bins_processed':False,
            'CAD_or_Gmsh_or_FEM_executed':False,
            'physical_4D_FEM_approved':False}
    Path('P10QK_M8_HYBRID_FINAL_CROSS_AUDIT_QA.json').write_text(json.dumps(result,indent=2)+'\n')
    print('P10QK_FINAL_INDEPENDENT_CROSS_AUDIT_PASS_AND_PHYSICS_FAIL_CLOSED',flush=True)


if __name__=='__main__':main()
