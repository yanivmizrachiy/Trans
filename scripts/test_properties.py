#!/usr/bin/env python3
"""Metamorphic, independent mathematical QA over actual source worksheet coordinates.

This suite extends example-based checks with general identities for rigid motions.
No third-party math services; uses an independent complex-number rotation model.
"""
import unittest
from itertools import product
from test_math import SOURCE,move,flip_v,flip_h,half,quarter,squared,area2

GRID=tuple(product(range(-6,7,3),range(-6,7,3)))
CENTERS=((-3,2),(0,0),(1,1),(4,-2))
ANGLES=(0,90,180,270)

def independent_rotate(point,center,angle):
    z=complex(*point)-complex(*center)
    rotation={0:1,90:1j,180:-1,270:-1j}[angle]
    result=complex(*center)+z*rotation
    return int(result.real),int(result.imag)

def oriented_area2(points):
    return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))

class TransformationIdentityTests(unittest.TestCase):
    def test_rotation_matches_independent_complex_model_on_every_source_point(self):
        pts=set(p for shape in SOURCE.values() for p in shape)|set(GRID)
        for center in CENTERS:
            for p in pts:
                self.assertEqual(quarter(p,center),independent_rotate(p,center,90))
                self.assertEqual(half(p,center),independent_rotate(p,center,180))

    def test_four_quarters_restore_every_point(self):
        for center in CENTERS:
            for p in GRID:
                q=p
                for _ in range(4):q=quarter(q,center)
                self.assertEqual(q,p)
                self.assertEqual(quarter(quarter(p,center),center),half(p,center))

    def test_composition_of_two_half_turns_equals_translation(self):
        for a in CENTERS:
            for b in CENTERS:
                delta=(2*(b[0]-a[0]),2*(b[1]-a[1]))
                for p in GRID:
                    self.assertEqual(half(half(p,a),b),move(p,*delta))

    def test_two_parallel_reflections_equal_translation(self):
        for a in (-4,-1,0,2,5):
            for b in (-3,0,1,4):
                for p in GRID:
                    self.assertEqual(flip_v(flip_v(p,a),b),move(p,2*(b-a),0))
                    self.assertEqual(flip_h(flip_h(p,a),b),move(p,0,2*(b-a)))

    def test_reflection_axis_is_exact_perpendicular_bisector(self):
        for k in (-4,-2,0,3):
            for x,y in GRID:
                xv,yv=flip_v((x,y),k)
                self.assertEqual(yv,y)
                self.assertEqual(x+xv,2*k)
                xh,yh=flip_h((x,y),k)
                self.assertEqual(xh,x)
                self.assertEqual(y+yh,2*k)
                self.assertEqual(flip_v((k,y),k),(k,y))
                self.assertEqual(flip_h((x,k),k),(x,k))

    def test_rigid_motions_preserve_all_original_pairwise_distances(self):
        for name,points in SOURCE.items():
            for center in CENTERS:
                for op in (lambda p:move(p,5,-3),lambda p:flip_v(p,center[0]),
                           lambda p:flip_h(p,center[1]),
                           lambda p:independent_rotate(p,center,90),
                           lambda p:independent_rotate(p,center,180),
                           lambda p:independent_rotate(p,center,270)):
                    out=[op(p) for p in points]
                    self.assertEqual(area2(points),area2(out),name)
                    for i in range(len(points)):
                        for j in range(i+1,len(points)):
                            self.assertEqual(squared(points[i],points[j]),squared(out[i],out[j]),name)

    def test_translation_rotation_keep_orientation_reflection_reverses_it(self):
        for name,shape in SOURCE.items():
            signed=oriented_area2(shape)
            self.assertNotEqual(signed,0,name)
            self.assertEqual(oriented_area2([move(p,2,-3) for p in shape]),signed,name)
            self.assertEqual(oriented_area2([independent_rotate(p,(1,-2),90) for p in shape]),signed,name)
            self.assertEqual(oriented_area2([flip_v(p,1) for p in shape]),-signed,name)
            self.assertEqual(oriented_area2([flip_h(p,-2) for p in shape]),-signed,name)

    def test_different_center_same_rotation_differs_by_one_translation(self):
        # R_c(p) = R_0(p) + c - R_0(c), independently of p.
        for center in CENTERS:
            q0=independent_rotate(center,(0,0),90)
            delta=(center[0]-q0[0],center[1]-q0[1])
            for p in GRID:
                self.assertEqual(independent_rotate(p,center,90),
                                 move(independent_rotate(p,(0,0),90),*delta))

if __name__=="__main__":
    unittest.main(verbosity=2)
