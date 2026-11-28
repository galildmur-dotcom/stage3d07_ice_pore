#!/usr/bin/env python3
"""Source-only synthetic unit checks: no P10GY ZIP needed."""
import math
import unittest
import numpy as np
from p10ha_spatial_kappa_source_pilot import dorfler, smooth


class P10HASourceTest(unittest.TestCase):
    def test_dorfler_minimality(self):
        w=np.array([0.,3.,2.,1.])
        for theta,n in ((0.35,1),(0.5,1),(0.65,2),(1.,3)):
            selection=dorfler(w,theta)
            self.assertEqual(int(selection.sum()),n)
            self.assertGreaterEqual(float(w[selection].sum()),theta*sum(w))

    def test_phi_seam_uses_direction_cosines(self):
        # Points on both sides of the ±pi seam must smooth each other.
        e=1e-5
        dirs=np.array([[0,math.cos(-math.pi+e),math.sin(-math.pi+e),0],
                       [0,math.cos(math.pi-e),math.sin(math.pi-e),0],
                       [0,1,0,0]],float)
        z,n=smooth(np.array([0.,1.,0.]),dirs,radial_band=1,angular_band=.4)
        self.assertAlmostEqual(z[0],z[1],places=4)
        self.assertEqual(n[0],2)
        self.assertEqual(n[1],2)
        self.assertTrue(np.all((z>=0)&(z<=1)))

    def test_constant_field_and_compact_support(self):
        pos=np.array([[0,1,0,0],[10,1,0,0],[20,1,0,0]],float)
        z,n=smooth(np.ones(3)*.3,pos,radial_band=.5,angular_band=.5)
        np.testing.assert_allclose(z,.3,atol=1e-14)
        self.assertEqual(n,[1,1,1])


if __name__=='__main__':unittest.main()
