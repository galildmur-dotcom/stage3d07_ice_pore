#!/usr/bin/env python3
"""P10KP: source-only C2 polar plateau for a *distinct* M8 R2 candidate.

No Gmsh, mesh, solver, external files or one-shot markers are touched.
The original P10KM field is supplied as kappa_base by the caller.
"""
from __future__ import annotations

import argparse
import json
import math


def smoothstep5(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * x * (10.0 + x * (-15.0 + 6.0 * x))


def polar_plateau(distance_mm: float, mu: float,
                  core_d_mm: float = 0.5, outer_d_mm: float = 1.0,
                  core_abs_mu: float = 0.8, outer_abs_mu: float = 0.6) -> float:
    """Unit plateau for d<=0.5mm and |mu|>=0.8; C2 outward taper.

    ``mu`` is the cosine of polar angle measured from the pore center.
    For a physical point, d=1000*(norm(x-center)-radius) in mm.
    """
    if not (0 <= distance_mm and -1 <= mu <= 1):
        raise ValueError('outside ice-side radial/polar domain')
    if not (0 <= core_d_mm < outer_d_mm and
            0 <= outer_abs_mu < core_abs_mu <= 1):
        raise ValueError('invalid C2 transition intervals')
    radial = 1 - smoothstep5((distance_mm - core_d_mm) /
                             (outer_d_mm - core_d_mm))
    angular = smoothstep5((abs(mu) - outer_abs_mu) /
                           (core_abs_mu - outer_abs_mu))
    return radial * angular


def kappa_r2(kappa_base: float, distance_mm: float, mu: float) -> float:
    """C2 blend with retained 4D-informed background, 0<=kappa<=1."""
    if not (math.isfinite(kappa_base) and 0 <= kappa_base <= 1):
        raise ValueError('P10KM kappa outside [0,1]')
    p = polar_plateau(distance_mm, mu)
    return max(0.0, min(1.0, kappa_base + (1 - kappa_base) * p))


def size_ratio(kappa: float) -> float:
    """Characteristic length ratio: at most 20% *nominal volume* change."""
    if not (0 <= kappa <= 1):
        raise ValueError('kappa outside [0,1]')
    return (1 - 0.20 * kappa) ** (1 / 3)


def selftest() -> dict:
    max_range_err = 0.0
    max_core_err = 0.0
    max_pole_sym_err = 0.0
    count = 0
    for base in (0., .0363, .3433, .3633, .7, 1.):
        for d in (0., .01, .25, .5, .500001, .6, .75, .999999, 1., 2., 5.):
            for mu in (-1., -.99, -.8, -.799999, -.7, -.6, 0., .6,
                       .7, .799999, .8, .99, 1.):
                k = kappa_r2(base, d, mu)
                v = size_ratio(k) ** 3
                max_range_err = max(max_range_err, max(0., -k, k-1., .8-v, v-1.))
                if d <= .5 and abs(mu) >= .8:
                    max_core_err = max(max_core_err, abs(k-1.))
                max_pole_sym_err = max(max_pole_sym_err,
                                       abs(k-kappa_r2(base,d,-mu)))
                count += 1
    assert max_range_err < 1e-12 and max_core_err < 1e-12
    assert max_pole_sym_err < 1e-12
    # C2 endpoint: numerical one-sided first and second derivative tend to zero.
    eps = 1e-4
    endpoint_curvature = max(abs(smoothstep5(eps)-smoothstep5(0.))/eps**2,
                             abs(smoothstep5(1.)-smoothstep5(1.-eps))/eps**2)
    assert endpoint_curvature < .002
    return {'protocol':'P10KP_M8_R2_C2_POLAR_PLATEAU_SOURCE_ONLY',
            'status':'PASS_MATHEMATICAL_UNIT_ONLY_NO_REAL_FIELD_NO_MESH_NO_FEM',
            'sample_count':count, 'core_d_mm':.5, 'outer_d_mm':1.,
            'core_abs_mu':.8, 'outer_abs_mu':.6,
            'blend':'kappa_base+(1-kappa_base)*radial_C2*angular_C2',
            'max_core_error':max_core_err, 'max_range_error':max_range_err,
            'max_pole_symmetry_error':max_pole_sym_err,
            'endpoint_second_derivative_proxy':endpoint_curvature,
            'mesh_attempts':0, 'FEM_attempts':0,
            'limitations':['Real P10KM 1200-bin interpolation not evaluated',
                           'M8 R2 regional Veff is unmeasured',
                           'D029 and D031 require a new distinct guarded native mesh']}


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(selftest(), indent=2, ensure_ascii=False))
