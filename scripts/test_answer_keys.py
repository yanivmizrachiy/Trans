#!/usr/bin/env python3
"""Check the actual printed teacher answer-key examples against worksheet geometry.

Unlike generic isometry unit tests, this check reads the 33 answer bullets
in docs/ANSWER_KEY.md and requires each computed answer to appear in the
correct source worksheet and question. It detects answer-key
regressions even when the transformation utilities remain mathematically valid.
"""
import re
import unittest
from test_math import ROOT, SOURCE, move, flip_v, flip_h, half, quarter, area2, plain

ANSWER=(ROOT/"docs"/"ANSWER_KEY.md").read_text(encoding="utf-8")

def show(point):
    return "("+str(point[0])+","+str(point[1])+")"

def expected(*points):
    return [show(p) for p in points]

def levels(name):
    heading=re.compile(r"^### [^\n]*`"+re.escape(name)+r"`\s*$",re.M)
    hits=list(heading.finditer(ANSWER))
    if len(hits)!=1:
        raise AssertionError(f"{name}: missing or duplicate answer key heading ({len(hits)})")
    part=ANSWER[hits[0].end():]
    m=re.search(r"^#{2,3} ",part,re.M)
    if m:part=part[:m.start()]
    bullets=re.findall(r"^- \*\*[^\n]+",part,re.M)
    if len(bullets)!=3:
        raise AssertionError(f"{name}: expected exactly three answer levels, got {len(bullets)}")
    return bullets

def verify_case(case,points,required,meaning):
    answer=levels(case)[points]
    normalized=answer.replace("−","-").replace(" ","").replace("–","-")
    for token in required:
        if token.replace("−","-").replace(" ","") not in normalized:
            raise AssertionError(f"{case} level {points+1} missing computed {token} ({meaning})")
    if len(answer)<65:
        raise AssertionError(f"{case} level {points+1}: explanation too short to guide a teacher")

class AnswerToWorksheetAlignment(unittest.TestCase):
    def test_all_thirty_three_bullets_are_present(self):
        for ident in SOURCE:
            with self.subTest(worksheet=ident):
                self.assertEqual(len(levels(ident)),3)

    def test_original_rectangles_and_area_are_consistent(self):
        name="orig-rectangles"; a=SOURCE[name]
        verify_case(name,0,expected(*(move(p,5,-2) for p in a))+["12","14"],"translation, area and perimeter")
        verify_case(name,1,["8","4","3"],"two rectangle orientations and four quadrants")
        verify_case(name,2,["2","אינסוף"],"first quadrant restrictions and unbounded rotations")

    def test_translations_and_parallel_reflections_match_all_vertices(self):
        name="orig-translation";a,b,c=SOURCE[name]
        verify_case(name,0,expected(*(move(p,2,0) for p in (a,b,c))),"entry translation")
        verify_case(name,1,expected(*(move(p,6,1) for p in (a,b,c)))+["(6,1)"],"reverse engineer vector")
        verify_case(name,2,["(2,2)","חילופי"],"composition and commutativity")
        name="orig-reflection";a,b,c=SOURCE[name]
        verify_case(name,0,expected(*(flip_v(p) for p in (a,b,c))),"vertical axis reflection")
        verify_case(name,1,expected(*(flip_v(p,1) for p in (a,b,c))),"line x=1 reflection")
        verify_case(name,2,[show(flip_v(flip_v(a,1),4)),"6"],"two parallel mirrors compose to translation")

    def test_rotations_and_compositions_match_all_vertices(self):
        name="orig-rotation";a,b,c=SOURCE[name]
        verify_case(name,0,expected(*(half(p) for p in (a,b,c))),"half-turn")
        verify_case(name,1,expected(*(quarter(p,(1,1)) for p in (a,b,c))),"quarter-turn around K")
        verify_case(name,2,expected(*(quarter(p) for p in (a,b,c)))+["(2,0)"],"center-shift comparison")
        name="orig-composition";a,b,c=SOURCE[name]
        verify_case(name,0,expected(*(move(p,2,1) for p in (a,b,c))),"basic shift")
        verify_case(name,1,[show(move(flip_v(a),2,1)),show(flip_v(move(a,2,1)))],"noncommuting orders")
        verify_case(name,2,["3-y","-y-3","6"],"algebraic reflections and translations")

    def test_symmetry_invariance_and_counterexamples(self):
        name="orig-symmetry";pts=SOURCE[name]
        verify_case(name,0,["A","C","B","D"],"fixed and swapped vertices")
        verify_case(name,1,["(0,3)","(0,-3)"],"non-invariant vertex B")
        verify_case(name,2,["x=0","y=0","180"],"rectangle symmetry axes and rotation")
        self.assertEqual(set(map(flip_v,pts)),set(pts))
        self.assertNotEqual(set(map(flip_h,pts)),set(pts))

    def test_conveyor_and_reflection_rotation_path_are_correct(self):
        name="orig-conveyor";pts=SOURCE[name]
        verify_case(name,0,expected(*(half(p) for p in pts))+["√5"],"180-degree rotation and radius")
        verify_case(name,1,["א׳","ב׳","ג׳","90"],"identify all candidate machines")
        sheet=(ROOT/"worksheets"/(name+".html")).read_text(encoding="utf-8").replace("−","-")
        key=levels(name)[1].replace("−","-")
        for title,op in (("א׳",half),("ב׳",flip_v),("ג׳",quarter)):
            computed=[op(p) for p in pts]
            for label,point in zip("ABC",computed):
                token=label+"′"+show(point)
                self.assertIn(token,sheet,f"Machine {title}: incomplete student prompt {token}")
                self.assertIn(token,key,f"Machine {title}: teacher key omits {token}")
        verify_case(name,2,["90","180","שיקופים"],"half-turn composition")
        name="orig-mirror-route";pts=SOURCE[name]
        verify_case(name,0,expected(*(flip_v(p) for p in pts)),"reflect all vertices in y axis")
        verify_case(name,1,expected(*(quarter(flip_v(p)) for p in pts)),"compare two valid image paths")
        verify_case(name,2,["(-y,-x)","y=-x"],"general identity and diagonal mirror")

    def test_distinct_rotation_centers_and_complex_polygon_match_key(self):
        name="orig-center-p";pts=SOURCE[name]
        verify_case(name,0,expected(*(half(p) for p in pts)),"180-degree turn around origin")
        verify_case(name,1,expected(*(half(p,(1,2)) for p in pts)),"180-degree turn around P")
        verify_case(name,2,[show(move(pts[0],4,0)),"(4,0)"],"two half-turns = translation")
        name="orig-symbol-turn";pts=SOURCE[name]
        verify_case(name,0,expected(half(pts[0]),half(pts[3])),"two distinct tracked vertices")
        verify_case(name,1,expected(*(half(p,(-1,1)) for p in pts)),"all seven polygon vertices")
        verify_case(name,2,[show(move(pts[0],2,0)),"(2,0)"],"two rotation centers produce shift")

    def test_robot_error_and_area_proof_are_both_documented(self):
        name="orig-robot-grid";pts=SOURCE[name]
        verify_case(name,0,expected(*(move(p,4,-2) for p in pts))+["4.5"],"translate and keep triangle area")
        verify_case(name,1,expected(*(flip_v(p,1) for p in pts))+["4.5"],"mirror, orientation and area")
        result=[move(flip_v(p,1),-5,-3) for p in pts]
        verify_case(name,2,expected(*result)+["(2,2)","6"],"detect erroneous vertex and area")
        self.assertEqual(area2(pts),9)
        self.assertEqual(area2(result),9)


class AdditionalOriginalKeys(unittest.TestCase):
    """The printed key for the three sheets written in 11.2026 must match independently computed images."""

    def section(self,start,stop):
        return ANSWER.split(start,1)[1].split(stop,1)[0]

    def test_community_hall_key(self):
        key=self.section("## שטיח המרכז הקהילתי","## מי צודק?")
        worksheet=plain((ROOT/"worksheets"/"rectangles.html").read_text(encoding="utf-8"))
        e,f,g,h=[(-2,-1),(4,-1),(4,1),(-2,1)]
        for token in ("E(-2,-1), F(4,-1), G(4,1), H(-2,1)","(-3,5)",
                      "E'"+show(move(e,-3,5))+", G'"+show(move(g,-3,5))+", H'"+show(move(h,-3,5)),
                      "E'"+show(flip_h(e,2))+", F'"+show(flip_h(f,2))+", G'"+show(flip_h(g,2))+", H'"+show(flip_h(h,2)),
                      "F'"+show(quarter(f,e))+", G'"+show(quarter(g,e))+", H'"+show(quarter(h,e)),
                      "אפשרות אחת","שתי אפשרויות","**לא.**","**חופף**"):
            self.assertIn(token,key)
        for prompt in ("F'(1,4)","y=2","0≤x≤5","0≤x≤7","E(-2,-1)"):
            self.assertIn(prompt,worksheet)

    def test_who_is_right_key(self):
        key=self.section("## מי צודק?","## תחנות ההעתקה")
        verdicts=re.findall(r"^(\d+)\. \*\*(נכון|לא נכון)\*\*",key,re.M)
        self.assertEqual([n for n,_ in verdicts],[str(i) for i in range(1,11)])
        self.assertEqual([v=="נכון" for _,v in verdicts],[True,True,False,True,True,False,False,True,True,False])
        self.assertIn(show(quarter((2,5))),key)
        self.assertIn(show(flip_v((5,3),2))[:3],key)
        worksheet=plain((ROOT/"worksheets"/"true-false.html").read_text(encoding="utf-8"))
        for token in ("(-4,0)","(2,5)","(5,2)","(3,-1)","x=2","(2,0)","(0,-3)"):
            self.assertIn(token,worksheet)

    def test_copying_stations_key(self):
        key=self.section("## תחנות ההעתקה","## קריטריונים")
        worksheet=plain((ROOT/"worksheets"/"triangle.html").read_text(encoding="utf-8"))
        pqr=[(2,1),(6,1),(2,4)]
        ops={"₁":lambda p:move(p,-3,2),"₂":flip_v,"₃":lambda p:half(p,(2,1)),"₄":quarter,"₅":lambda p:flip_h(p,-1)}
        for sub,op in ops.items():
            img=[op(p) for p in pqr]
            with self.subTest(station=sub):
                self.assertIn(", ".join(n+sub+show(p) for n,p in zip("PQR",img)),key)
                self.assertEqual(area2(img),area2(pqr))
        for token in ("PQ=4","PR=3","QR=5","2 ו־5","(2,0)","(4,-2)","(-4,2)","(2,-4)","y=x","O(0,0)"):
            self.assertIn(token,key)
        for prompt in ("תחנה 5","(-3,2)","משימות המשך"):
            self.assertIn(prompt,worksheet)
        self.assertEqual([half((p[1],-p[0])) for p in pqr],[quarter(p) for p in pqr])
        self.assertEqual([(p[1],p[0]) for p in (flip_h(q) for q in pqr)],[quarter(p) for p in pqr])

if __name__=="__main__":
    unittest.main(verbosity=2)
