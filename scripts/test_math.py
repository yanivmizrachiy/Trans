#!/usr/bin/env python3
"""Exact mathematical checks for Yaniv Raz's original transformation worksheets."""
from pathlib import Path
from html import unescape
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE={
    "orig-rectangles":[(-4,0),(0,0),(0,3),(-4,3)],
    "orig-translation":[(-4,-1),(-1,-1),(-4,2)],
    "orig-reflection":[(-3,1),(-1,1),(-3,4)],
    "orig-rotation":[(1,0),(3,0),(1,2)],
    "orig-composition":[(1,1),(3,1),(1,2)],
    "orig-symmetry":[(-2,0),(0,3),(2,0),(0,-1)],
    "orig-conveyor":[(1,2),(4,2),(2,4)],
    "orig-mirror-route":[(-2,1),(0,1),(-2,3)],
    "orig-center-p":[(-3,1),(-1,1),(-1,4)],
    "orig-symbol-turn":[(-4,-1),(-1,-1),(-1,0),(1,1),(-1,2),(-1,3),(-4,3)],
    "orig-robot-grid":[(-5,1),(-2,1),(-5,4)]
}
def move(p,dx,dy):return p[0]+dx,p[1]+dy
def flip_v(p,k=0):return 2*k-p[0],p[1]
def flip_h(p,k=0):return p[0],2*k-p[1]
def half(p,c=(0,0)):return 2*c[0]-p[0],2*c[1]-p[1]
def quarter(p,c=(0,0)):return c[0]-(p[1]-c[1]),c[1]+p[0]-c[0]
def squared(a,b):return (a[0]-b[0])**2+(a[1]-b[1])**2
def area2(pts):
    return abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(pts,pts[1:]+pts[:1])))

class MathQuality(unittest.TestCase):
    def test_diagrams_match_written_coordinates(self):
        for name,points in SOURCE.items():
            with self.subTest(name=name):
                doc=(ROOT/"worksheets"/(name+".html")).read_text(encoding="utf-8")
                found=re.search(r'data-shape=[\x22\x27]([^\x22\x27]+)[\x22\x27]',doc)
                self.assertIsNotNone(found)
                raw=[tuple(map(int,p.split(","))) for p in found.group(1).split(";")]
                self.assertEqual(raw,points)
                self.assertGreater(area2(points),0)
                self.assertTrue(all(abs(x)<=7 and abs(y)<=7 for x,y in points))
                self.assertEqual(len(set(points)),len(points))
                self.assertIn("יצירה מקורית: יניב רז",doc)
                self.assertIn("../assets/raz-logo.svg",doc)
                self.assertEqual(doc.count('class="level"')+doc.count("class='level'"),3)

    def test_isometries_preserve_distances_and_area(self):
        for name,pts in SOURCE.items():
            for op in (lambda p:move(p,3,-2),lambda p:flip_v(p,1),lambda p:flip_h(p),
                       lambda p:quarter(p,(1,2)),lambda p:half(p,(-1,1))):
                result=list(map(op,pts))
                with self.subTest(name=name,op=str(op)):
                    self.assertEqual(area2(result),area2(pts))
                    for i in range(len(pts)):
                        for j in range(i+1,len(pts)):
                            self.assertEqual(squared(pts[i],pts[j]),squared(result[i],result[j]))

    def test_rectangles(self):
        pts=SOURCE["orig-rectangles"]
        self.assertEqual([move(p,5,-2) for p in pts],[(1,-2),(5,-2),(5,1),(1,1)])
        self.assertEqual(area2(pts),24)
        choices=[(w,h,sx,sy) for w,h in [(4,3),(3,4)] for sx in [-1,1] for sy in [-1,1]]
        self.assertEqual(len(choices),8)
        inside=[x for x in choices if (2+x[2]*x[0]>=0 and 1+x[3]*x[1]>=0)]
        self.assertEqual(len(inside),2)

    def test_translation(self):
        a,b,c=SOURCE["orig-translation"]
        self.assertEqual(move(a,6,1),(2,0))
        self.assertEqual([move(p,6,1) for p in (b,c)],[(5,0),(2,3)])
        self.assertEqual(move(move(a,3,-2),-1,4),move(a,2,2))

    def test_reflection(self):
        a,b,c=SOURCE["orig-reflection"]
        self.assertEqual([flip_v(p,1) for p in (a,b,c)],[(5,1),(3,1),(5,4)])
        self.assertEqual(flip_v(flip_v(a,1),4),(3,1))

    def test_rotation(self):
        a,b,c=SOURCE["orig-rotation"]
        self.assertEqual([quarter(p,(1,1)) for p in (a,b,c)],[(2,1),(2,3),(0,1)])
        for p in (a,b,c):
            self.assertEqual(move(quarter(p),2,0),quarter(p,(1,1)))

    def test_composition(self):
        a=SOURCE["orig-composition"][0]
        self.assertEqual(move(flip_v(a),2,1),(1,2))
        self.assertEqual(flip_v(move(a,2,1)),(-3,2))
        for p in SOURCE["orig-composition"]:
            r1=move(flip_h(p),0,3)
            r2=flip_h(move(p,0,3))
            self.assertEqual(r1[1]-r2[1],6)

    def test_symmetry(self):
        pts=SOURCE["orig-symmetry"]
        self.assertEqual(set(map(flip_v,pts)),set(pts))
        self.assertNotEqual(set(map(flip_h,pts)),set(pts))
        self.assertNotEqual(set(map(half,pts)),set(pts))

    def test_conveyor(self):
        pts=SOURCE["orig-conveyor"]
        self.assertEqual([half(p) for p in pts],[(-1,-2),(-4,-2),(-2,-4)])
        self.assertEqual([flip_v(p) for p in pts],[(-1,2),(-4,2),(-2,4)])
        self.assertEqual([quarter(p) for p in pts],[(-2,1),(-2,4),(-4,2)])
        self.assertEqual(quarter(quarter(pts[2])),half(pts[2]))
        # Two collinear point images do not always distinguish a reflection
        # from a half-turn about a different center; the third does.
        for p in pts[:2]:
            self.assertEqual(flip_v(p),half(p,(0,2)))
        self.assertNotEqual(flip_v(pts[2]),half(pts[2],(0,2)))

    def test_mirror_route(self):
        for p in SOURCE["orig-mirror-route"]:
            self.assertEqual(quarter(flip_v(p)),flip_h(quarter(p)))
            self.assertEqual(quarter(flip_v(p)),(-p[1],-p[0]))

    def test_rotation_center(self):
        p=SOURCE["orig-center-p"][0]
        self.assertEqual(half(p,(1,2)),(5,3))
        self.assertEqual(half(half(p,(1,2)),(3,2)),(1,1))
        self.assertEqual(half(half(p,(1,2)),(3,2)),move(p,4,0))

    def test_symbol_turn(self):
        pts=SOURCE["orig-symbol-turn"]
        self.assertEqual([half(p,(-1,1)) for p in pts],[(2,3),(-1,3),(-1,2),(-3,1),(-1,0),(-1,-1),(2,-1)])
        for p in pts:
            self.assertEqual(half(half(p,(-1,1)),(0,1)),move(p,2,0))

    def test_robot_error(self):
        a,b,c=SOURCE["orig-robot-grid"]
        self.assertEqual([move(p,4,-2) for p in (a,b,c)],[(-1,-1),(2,-1),(-1,2)])
        self.assertEqual([flip_v(p,1) for p in (a,b,c)],[(7,1),(4,1),(7,4)])
        output=[move(flip_v(p,1),-5,-3) for p in (a,b,c)]
        self.assertEqual(output,[(2,-2),(-1,-2),(2,1)])
        self.assertNotEqual(output[2],(2,2))
        self.assertEqual(area2(output),9)
        self.assertNotEqual(area2(output[:2]+[(2,2)]),area2(output))

if __name__=="__main__":unittest.main(verbosity=2)
