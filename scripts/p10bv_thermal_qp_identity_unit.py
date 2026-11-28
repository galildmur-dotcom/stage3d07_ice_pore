#!/usr/bin/env python3
"""Independent local thermal Tet10/Tri6 shape-contraction identity (P10BV).

Reimplements the published P10L quadrature identities on ONE synthetic curved
Tet10 and one synthetic Robin Tri6 face. No ice FEM, no production C++ calls.
Central finite differences are used ONLY as an independent derivative control.
The nonzero Robin face velocity is intentionally synthetic; for physical pore-R
with a 5 mm velocity cutoff, the remote top face should normally be stationary.
"""

from __future__ import annotations

import math

G4 = (
    (0.0694318442029737, 0.1739274225687269),
    (0.3300094782075719, 0.3260725774312731),
    (0.6699905217924281, 0.3260725774312731),
    (0.9305681557970262, 0.1739274225687269),
)
EDGES = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
DL4 = ((-1., -1., -1.), (1., 0., 0.), (0., 1., 0.), (0., 0., 1.))
DL3 = ((-1., -1.), (1., 0.), (0., 1.))
RHOC = 920.3 * 1960.
K = 2.4
H = 24.


def dot(a, b):
    return math.fsum(x*y for x, y in zip(a, b))


def add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def mul(a, k):
    return tuple(x*k for x in a)


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def norm(a):
    return math.sqrt(dot(a, a))


def sumvec(vs, coeffs):
    weights = tuple(coeffs)
    return tuple(math.fsum(v[k]*w for v, w in zip(vs, weights)) for k in range(3))


def tet10_shape(r, s, t):
    L = (1-r-s-t, r, s, t)
    N = [L[i]*(2*L[i]-1) for i in range(4)]
    d = [tuple((4*L[i]-1)*DL4[i][k] for k in range(3)) for i in range(4)]
    for a, b in EDGES:
        N.append(4*L[a]*L[b])
        d.append(tuple(4*(L[a]*DL4[b][k]+L[b]*DL4[a][k])
                       for k in range(3)))
    return N, d


def tri6_shape(r, s):
    L = (1-r-s, r, s)
    N = [L[i]*(2*L[i]-1) for i in range(3)]
    d = [tuple((4*L[i]-1)*DL3[i][k] for k in range(2)) for i in range(3)]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        N.append(4*L[a]*L[b])
        d.append(tuple(4*(L[a]*DL3[b][k]+L[b]*DL3[a][k])
                       for k in range(2)))
    return N, d


def geometry():
    corners = ((0., 0., 0.), (.002, 0., 0.), (0., .0015, 0.),
               (0., 0., .0012))
    mids = [mul(add(corners[a], corners[b]), .5) for a, b in EDGES]
    # Curvature without changing node ordering or sign of the Jacobian.
    mids[0] = add(mids[0], (0., 0., .000021))
    mids[1] = add(mids[1], (0., 0., -.000014))
    mids[4] = add(mids[4], (0., .000017, 0.))
    nodes = corners+tuple(mids)
    velocity = tuple((.20+.08*math.sin(i), -.13+.07*math.cos(i),
                      .17-.04*math.sin(2*i)) for i in range(10))
    return nodes, velocity


def contract(nodes, velocity, psi, theta, theta_prev, dt, ambient,
             with_derivative):
    mass = diffusion = robin = 0.
    dmass = ddiffusion = drobin = 0.
    max_unity = 0.
    for ga, gb, gc in ((a, b, c) for a in G4 for b in G4 for c in G4):
        a, b, c = ga[0], gb[0], gc[0]
        r, s, t = a, (1-a)*b, (1-a)*(1-b)*c
        N, d = tet10_shape(r, s, t)
        quadrature_weight = ga[1]*gb[1]*gc[1]*(1-a)**2*(1-b)
        J = [sumvec(nodes, (q[k] for q in d)) for k in range(3)]
        DJ = [sumvec(velocity, (q[k] for q in d)) for k in range(3)]
        dr, ds, dv = J
        drp, dsp, dvp = DJ
        A, B, C = cross(ds, dv), cross(dv, dr), cross(dr, ds)
        DA = add(cross(dsp, dv), cross(ds, dvp))
        DB = add(cross(dvp, dr), cross(dv, drp))
        DC = add(cross(drp, ds), cross(dr, dsp))
        det = dot(dr, A)
        ddet = dot(drp, A)+dot(dr, DA)
        if not det > 0:
            raise AssertionError("Synthetic Tet10 has nonpositive Jacobian")
        w, dw = quadrature_weight*det, quadrature_weight*ddet
        grads = []
        dgrads = []
        for dd in d:
            g = mul(add(add(mul(A, dd[0]), mul(B, dd[1])),
                        mul(C, dd[2])), 1/det)
            dg = sub(mul(add(add(mul(DA, dd[0]), mul(DB, dd[1])),
                             mul(DC, dd[2])), 1/det), mul(g, ddet/det))
            grads.append(g)
            dgrads.append(dg)
        p = dot(N, psi)
        temp_delta = dot(N, (x-y for x, y in zip(theta, theta_prev)))
        gp = sumvec(grads, psi)
        gt = sumvec(grads, theta)
        dgp = sumvec(dgrads, psi)
        dgt = sumvec(dgrads, theta)
        mass += RHOC*w*p*temp_delta
        diffusion += dt*K*w*dot(gp, gt)
        dmass += RHOC*dw*p*temp_delta
        ddiffusion += dt*K*(dw*dot(gp, gt)+w*(dot(dgp, gt)+dot(gp, dgt)))
        max_unity = max(max_unity, norm(sumvec(grads, (1. for _ in grads))),
                        norm(sumvec(dgrads, (1. for _ in dgrads))))
    # Top Robin face uses Tet10 local face [0,1,2,4,5,6] for this toy.
    ids = (0, 1, 2, 4, 5, 6)
    face_nodes = [nodes[i] for i in ids]
    face_velocities = [velocity[i] for i in ids]
    for ga, gb in ((a, b) for a in G4 for b in G4):
        r, s = ga[0], (1-ga[0])*gb[0]
        N, d = tri6_shape(r, s)
        du = sumvec(face_nodes, (q[0] for q in d))
        dv = sumvec(face_nodes, (q[1] for q in d))
        ddu = sumvec(face_velocities, (q[0] for q in d))
        ddv = sumvec(face_velocities, (q[1] for q in d))
        normal = cross(du, dv)
        dnormal = add(cross(ddu, dv), cross(du, ddv))
        weight = ga[1]*gb[1]*(1-ga[0])
        area = weight*norm(normal)
        darea = weight*dot(normal, dnormal)/norm(normal)
        p = dot(N, (psi[i] for i in ids))
        t = dot(N, (theta[i] for i in ids))
        robin += dt*H*area*p*(t-ambient)
        drobin += dt*H*darea*p*(t-ambient)
    if with_derivative:
        return (dmass, ddiffusion, drobin, max_unity)
    return mass+diffusion+robin


def main():
    nodes, velocity = geometry()
    psi = tuple(.20+.06*math.cos(i*1.4) for i in range(10))
    theta = tuple(-1.1+.11*i+.15*math.sin(i) for i in range(10))
    theta_prev = tuple(-.9+.07*i+.10*math.cos(i) for i in range(10))
    eps = 1e-8  # meters: independent central perturbation check only.
    errors = []
    for dt in (150., 75., 50., 25.):
        a, b, c, unity = contract(nodes, velocity, psi, theta, theta_prev,
                                  dt, ambient=-2.1, with_derivative=True)
        plus = tuple(add(x, mul(v, eps)) for x, v in zip(nodes, velocity))
        minus = tuple(sub(x, mul(v, eps)) for x, v in zip(nodes, velocity))
        forward = contract(plus, velocity, psi, theta, theta_prev,
                           dt, ambient=-2.1, with_derivative=False)
        backward = contract(minus, velocity, psi, theta, theta_prev,
                            dt, ambient=-2.1, with_derivative=False)
        independent_fd = (forward-backward)/(2*eps)
        analytic = math.fsum((a, b, c))
        err = abs(analytic-independent_fd)/max(1e-10, abs(analytic))
        if err > 2e-6 or unity > 2e-9:
            raise AssertionError(f"dt={dt} geometry JVP mismatch rel={err} "
                                 f"unity={unity}")
        errors.append(err)
        print(f"P10BV_TET10_TRI6_UNIT_OK dt_s={int(dt)} "
              f"mass={a:+.12e} diffusion={b:+.12e} "
              f"robin={c:+.12e} total={analytic:+.12e} "
              f"independent_fd_rel={err:.3e}")
    print("P10BV_LOCAL_HEAT_SHAPE_IDENTITY_OK checks=4 FEM=0 "
          f"max_independent_fd_rel={max(errors):.3e} "
          "production_Cpp_executed=NO")


if __name__ == "__main__":
    main()
