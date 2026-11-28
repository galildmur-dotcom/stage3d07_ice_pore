#!/usr/bin/env python3
"""Gmsh 4.15.2 tetrahedron10 edge enumeration, synthetic linear-field check."""
import numpy as np
import P10HE_build_view as builder

EDGES=((0,1),(1,2),(2,0),(3,0),(3,2),(3,1))
assert builder.GMSH_TET10_EDGES == EDGES
corner=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],float)
middle=np.array([(corner[a]+corner[b])*.5 for a,b in EDGES])
allnodes=np.vstack([corner,middle])
linear=lambda p:0.2+0.1*p[:,0]+0.15*p[:,1]+0.22*p[:,2]
v=linear(allnodes)
err=max(abs(v[4+i]-.5*(v[a]+v[b])) for i,(a,b) in enumerate(EDGES))
assert err<1e-15
print('P10HG_GMSH_TET10_NODE_ORDER_SELFTEST_PASS',format(err,'.3g'),flush=True)
