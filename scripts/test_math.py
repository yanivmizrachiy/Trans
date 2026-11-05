#!/usr/bin/env python3
"""Exact mathematical checks for Yaniv Raz's original transformation worksheets."""
from pathlib import Path
from html import unescape
import re
import unittest
import manifest as M

ROOT=M.ROOT
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
    def test_source_table_covers_exactly_the_manifest_originals(self):
        self.assertEqual(set(SOURCE),set(M.ORIGINAL))

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
                self.assertIn("הדף נערך ע״י יניב רז · מדריך מחוזי חט״ב בעיר ירושלים",doc)
                self.assertIn("../assets/logo.png",doc)
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


def plain(text):return text.replace("−","-").replace("′","'")
ADDITIONAL={"rectangles":[(-2,-1),(4,-1),(4,1),(-2,1)],"triangle":[(2,1),(6,1),(2,4)]}
def orientation(points):
    a,b,c=points[:3]
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])

class AdditionalOriginalSheets(unittest.TestCase):
    """Independent arithmetic for the three sheets written from scratch in 11.2026
    (rectangles, true-false, triangle): the drawing, the prompts and every answer."""

    def test_rewritten_sheets_are_marked_original_without_graded_levels(self):
        for name in ("rectangles","true-false","triangle"):
            doc=(ROOT/"worksheets"/(name+".html")).read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertIn(name,M.IMPORTED)
                self.assertEqual(M.WORKSHEET_SOURCE[name],"original-2026-11")
                self.assertNotIn("נכתב לחוברת",doc)
                # the booklet's logo footer on every printed page
                self.assertEqual(doc.count("assets/logo.png"),M.WORKSHEET_PAGES[name])
                self.assertNotIn("הדף נערך ע״י יניב רז · מדריך מחוזי חט״ב בעיר ירושלים",doc)

    def test_community_hall_rectangle(self):
        doc=(ROOT/"worksheets"/"rectangles.html").read_text(encoding="utf-8")
        pts=ADDITIONAL["rectangles"]
        self.assertIn('data-shape="-2,-1;4,-1;4,1;-2,1"',doc)
        self.assertEqual(area2(pts),2*12)
        self.assertEqual(squared(pts[0],pts[1]),36);self.assertEqual(squared(pts[1],pts[2]),4)
        e,f,g,h=pts
        self.assertEqual(move(f,-3,5),(1,4))
        self.assertEqual([move(p,-3,5) for p in (e,g,h)],[(-5,4),(1,6),(-5,6)])
        self.assertEqual([flip_h(p,2) for p in pts],[(-2,5),(4,5),(4,3),(-2,3)])
        self.assertEqual(set(flip_h(p,2) for p in pts),set(move(p,0,4) for p in pts))
        def fits(w,h):return [(a,b) for a,b in ((6,2),(2,6)) if a<=w and b<=h]
        self.assertEqual(fits(5,7),[(2,6)]);self.assertEqual(fits(7,7),[(6,2),(2,6)])
        self.assertEqual([quarter(p,e) for p in (f,g,h)],[(-2,5),(-4,5),(-4,-1)])
        self.assertEqual(area2([quarter(p,e) for p in pts]),area2(pts))
        self.assertEqual(3*4,6*2);self.assertNotEqual({3,4},{6,2})

    def test_who_is_right_ten_claims(self):
        doc=(ROOT/"worksheets"/"true-false.html").read_text(encoding="utf-8")
        verdicts=[
            flip_h((-4,0))==(-4,0),
            move((-1,5),3,-2)==(2,3),
            quarter((2,5))==(5,2),
            flip_h(flip_v((3,-1)))==half((3,-1)),
            True,
            all(quarter(p) in [(1,1),(3,1),(3,3),(1,3)] for p in [(1,1),(3,1),(3,3),(1,3)]),
            4*6==3*8 and {4,6}=={3,8},
            move(move((1,1),2,0),0,-3)==move(move((1,1),0,-3),2,0),
            flip_v((5,3),2)==(-1,3),
            squared((0,0),quarter((3,4)))!=25,
        ]
        self.assertEqual(verdicts,[True,True,False,True,True,False,False,True,True,False])
        self.assertEqual(quarter((2,5)),(-5,2))
        self.assertEqual([quarter(p,(2,2)) for p in [(1,1),(3,1),(3,3),(1,3)]],[(3,1),(3,3),(1,3),(1,1)])
        self.assertEqual(doc.count('<section class="q"'),10)

    def test_copying_stations_triangle(self):
        doc=(ROOT/"worksheets"/"triangle.html").read_text(encoding="utf-8")
        pqr=ADDITIONAL["triangle"]
        self.assertIn('const pts=[[2,1],[6,1],[2,4]]',doc)
        self.assertEqual([squared(pqr[0],pqr[1]),squared(pqr[0],pqr[2]),squared(pqr[1],pqr[2])],[16,9,25])
        stations={1:lambda p:move(p,-3,2),2:flip_v,3:lambda p:half(p,(2,1)),4:quarter,5:lambda p:flip_h(p,-1)}
        images={k:[op(p) for p in pqr] for k,op in stations.items()}
        self.assertEqual(images[1],[(-1,3),(3,3),(-1,6)])
        self.assertEqual(images[2],[(-2,1),(-6,1),(-2,4)])
        self.assertEqual(images[3],[(2,1),(-2,1),(2,-2)])
        self.assertEqual(images[4],[(-1,2),(-1,6),(-4,2)])
        self.assertEqual(images[5],[(2,-3),(6,-3),(2,-6)])
        self.assertNotEqual(images[5],[move(p,0,-4) for p in pqr])
        for k,img in images.items():
            with self.subTest(station=k):
                self.assertEqual(area2(img),area2(pqr))
                self.assertEqual((orientation(img)<0),k in (2,5))
        cw=lambda p:(p[1],-p[0])
        self.assertEqual([half(cw(p)) for p in pqr],images[4])
        self.assertEqual([(p[1],p[0]) for p in (flip_h(q) for q in pqr)],images[4])

if __name__=="__main__":unittest.main(verbosity=2)
