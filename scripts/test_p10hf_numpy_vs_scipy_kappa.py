#!/usr/bin/env python3
"""Independent research-only parity test; SciPy NOT required on user's Windows."""
import sys
from pathlib import Path
import unittest
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0,str(Path(__file__).resolve().parent))
import p10hc_continuous_kappa_geo as field


def scipy_reference(source, values, queries,den):
    scale=np.array([field.R_SCALE,field.A_SCALE,field.A_SCALE,field.A_SCALE])
    src=source/scale
    dst=queries/scale
    tree=cKDTree(src)
    out=np.zeros(len(dst))
    for i,ids in enumerate(tree.query_ball_point(dst,1.0)):
        if not ids:continue
        q=np.linalg.norm(src[ids]-dst[i],axis=1)
        w=np.maximum(1-q,0)**4*(4*q+1)
        out[i]=np.dot(w,values[ids])/(w.sum()+field.EPS)/den
    return np.clip(out,0,1)


class Parity(unittest.TestCase):
    def test_exact_field_and_polars(self):
        root=Path(__file__).resolve().parents[1]
        p=root/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124'
        src,v25,v36,k25,k36,qa=field.load_centers(
            p/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',p/'P10HA_KAPPA_QA.json')
        rng=np.random.default_rng(20261124)
        dirs=rng.normal(size=(2000,3))
        dirs/=np.linalg.norm(dirs,axis=1)[:,None]
        dmm=rng.uniform(0,25,size=2000)
        cart=np.array(field.C)+dirs*(field.PORE_R+dmm[:,None]/1000)
        queries=np.concatenate([src,field.physical_query(cart)],axis=0)
        den=qa['mechanical_only_25_36_shared_smoothing_denominator']
        new=field.rbf_at_points(src,v25,queries,den)
        old=scipy_reference(src,v25,queries,den)
        self.assertLess(float(np.max(np.abs(new-old))),1e-12)
        self.assertLess(float(np.max(np.abs(new[:1200]-k25))),1e-9)
        self.assertTrue(np.isfinite(new).all())


if __name__=='__main__':unittest.main()
