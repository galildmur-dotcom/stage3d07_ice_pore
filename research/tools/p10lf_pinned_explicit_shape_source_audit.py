#!/usr/bin/env python3
"""P10LF read-only source contract and analytic quotient split check.

No FEA, mesh generation, source modification, numerical FD derivative, or marker.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import zipfile

import numpy as np
import pandas as pd


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def objective(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        table=pd.read_csv(io.BytesIO(z.read('P10W_ANALYTIC_ADJOINT.csv')))
    row=table[table.functional=='jpeak']
    assert len(row)==1
    return {'objective':float(row.iloc[0].objective),
            'B6_volume_m3':float(row.iloc[0].B6_volume_m3)}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source-dir',required=True)
    for x in ('m7','m8','m9','out'):ap.add_argument('--'+x,required=True)
    a=ap.parse_args()
    from pathlib import Path
    src=Path(a.source_dir)
    dd=src/'stage3d10dd_4d_partition.hpp'
    v=src/'src/stage3d10v_analytic_shape.hpp'
    f=src/'src/stage3d10f_functional_adjoint.hpp'
    k=src/'src/stage3d10k_h0_coupled_pilot.cpp'
    w=src/'src/stage3d10p_partial_audit.cpp'
    for path in (dd,v,f,k,w):assert path.is_file()
    ds=dd.read_text(encoding='utf8');vs=v.read_text(encoding='utf8')
    fs=f.read_text(encoding='utf8');ks=k.read_text(encoding='utf8')
    ws=w.read_text(encoding='utf8')
    required={
      'P10DD_local_objective_quotient':
        'out.cells[i].part.explicit_objective=weight*' in ds and
        '(dnumerator[i]-mean*dvolume[i])/out.observed_volume' in ds,
      'P10DD_geometry_volume_and_law':
        'dnumerator[cell_id]+=dv*src.value+qp.volume*dpoint' in ds,
      'P10DD_stress_jvp':
        'p10b::euclid_dot(src.lambda_sigma,law.d_sigma)' in ds,
      'P10V_full_quotient_parity':
        'out.objective[k]=(d_numerator[k]-' in vs and
        'average*out.observed_volume_derivative)/out.observed_volume' in vs,
      'same_reference_P10DD_to_P10V_per_step':
        'mechanical step explicit' in ws and
        'weights[1]*analytic.objective[1]' in ws,
      'centroid_elementwise_B6_mask':
        'for(int j=0;j<4;++j)center=center+mesh.nodes[mesh.tets[e][j]]*.25' in ks and
        'norm(center-V{0,0,.03})<.006' in ks,
      'radial_normal_C2_velocity':
        'if(mode=="R" || mode=="radius")return n*f' in vs and
        'f=1.-t*t*(3.-2.*t)' in vs,
    }
    # PeakMoment point source assigns only spectral stress sensitivity.
    energy=fs.index('if(kind==Kind::Energy)')
    end_energy=fs.index('const auto eig=jacobi_symmetric_3x3',energy)
    after=fs[end_energy:fs.index('struct Sources {',end_energy)]
    required['PeakMoment_no_direct_strain_or_direct_history']= (
       'out.lambda_sigma=spectral_gradient(eig,dev)' in after and
       'out.lambda_next.' not in after and 'out.direct_strain[' not in after)
    assert all(required.values()),str(required)
    # Exact independent complex-step of the normalized spatial quotient.
    # Synthetic fields only; this does not run the constitutive model or solver.
    rng=np.random.default_rng(1007)
    maxima=[]
    for n in (3,1200):
        vol=rng.uniform(.001,1.5,n)
        value=rng.lognormal(-1,1,n)
        dv=rng.normal(size=n)*.1
        dp=rng.normal(size=n)*.2
        volume=vol.sum();mean=(vol@value)/volume
        geometric=(dv@(value-mean))/volume
        stress_chain=(vol@dp)/volume
        split=geometric+stress_chain
        z=1e-30j
        complex_result=((vol+z*dv)@(value+z*dp))/(vol+z*dv).sum()
        err=abs(split-complex_result.imag/1e-30)
        assert err<1e-11,(n,err)
        maxima.append(float(err))
    observations={m:objective(getattr(a,m)) for m in ('m7','m8','m9')}
    delta_volume={pair:float(observations[b]['B6_volume_m3']/observations[x]['B6_volume_m3']-1)
                  for pair,x,b in [('M7_to_M8','m7','m8'),('M8_to_M9','m8','m9')]}
    delta_objective={pair:float(observations[b]['objective']/observations[x]['objective']-1)
                     for pair,x,b in [('M7_to_M8','m7','m8'),('M8_to_M9','m8','m9')]}
    report={'protocol':'P10LF_PINNED_SOURCE_EXPLICIT_PEAKMOMENT_QUOTIENT_AUDIT',
            'status':'PASS_SOURCE_CONTRACT_AND_COMPLEX_STEP_QUOTIENT_ONLY',
            'source_sha256':{str(path.relative_to(src)):sha(path) for path in (dd,v,f,k,w)},
            'static_contracts':required,
            'synthetic_complex_step_quotient_max_abs_error':max(maxima),
            'explicit_PeakMoment_formula':
              'w/V sum_QP[dvol*(src.value-Jbar) + vol*lambda_sigma_dot_law.d_sigma]',
            'first_term':'normalized geometric volume/Jacobian (includes global Jbar)',
            'second_term':'constitutive spectral stress sensitivity via Tet10 dgrad,dstrain and material JVP',
            'PeakMoment_direct_history_and_strain_source':'ZERO; adjoint history contribution remains separate',
            'B6_mask':'element centroid radius<6mm; entire selected element, fixed per mesh; differs across meshes',
            'observations':observations,'B6_relative_volume_changes':delta_volume,
            'objective_relative_changes':delta_objective,
            'cannot_identify':'separate two explicit terms in existing P10DD CSV; need new diagnostic columns or a saved-state replay',
            'limitations':['No forward/adjoint state replay, physical local error estimate, or mesh convergence proof',
                           'Complex-step test is synthetic algebra, not a test of nonlinear EDV constitutive JVP',
                           'B6 volume change cannot by itself quantify objective mask-induced derivative error'],
            'FEM_attempts':0,'mesh_attempts':0}
    from pathlib import Path
    out=Path(a.out);assert not out.exists()
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'status':report['status'],'static_contracts':required,
                      'synthetic_max_abs_error':max(maxima),
                      'B6_relative_volume_changes':delta_volume,
                      'objective_relative_changes':delta_objective},indent=2))


if __name__=='__main__':main()
