#!/usr/bin/env python3
"""Check the actual printed teacher answer-key examples against worksheet geometry.

Unlike generic isometry unit tests, this check reads the 33 answer bullets
in docs/ANSWER_KEY.md and requires each computed answer to appear in the
correct source worksheet and correct difficulty tier. It detects answer-key
regressions even when the transformation utilities remain mathematically valid.
"""
from pathlib import Path
import re
import unittest
from test_math import ROOT, SOURCE, move, flip_v, flip_h, half, quarter, area2, squared

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


class ImportedFollowUpAnswers(unittest.TestCase):
    """Cross-check real imported worksheet prompts and independently computed answers."""

    def test_congruent_rectangle_does_not_require_translation(self):
        worksheet=(ROOT/"worksheets"/"rectangles.html").read_text(encoding="utf-8")
        section=ANSWER.split("## מלבנים חופפים",1)[1].split("## נכון / לא נכון",1)[0]
        self.assertIn("ה. חשיבה ביקורתית",worksheet)
        self.assertIn("| ה. האם חפיפה מחייבת הזזה? |",section)
        self.assertIn("סיבוב",section)
        self.assertIn("הזזה בלבד",section)
        rectangle=[(-3,-1),(-3,3),(2,3),(2,-1)]
        rotated=[quarter(p) for p in rectangle]
        before=(rectangle[3][0]-rectangle[0][0],rectangle[3][1]-rectangle[0][1])
        after=(rotated[3][0]-rotated[0][0],rotated[3][1]-rotated[0][1])
        self.assertEqual(before,(5,0))
        self.assertEqual(after,(0,5))
        self.assertEqual(area2(rectangle),area2(rotated))
        self.assertNotEqual(before,after)

    def test_five_triangle_images_and_four_followup_solutions(self):
        worksheet=(ROOT/"worksheets"/"triangle.html").read_text(encoding="utf-8")
        section=ANSWER.split("## זיהוי טרנספורמציה של משולש",1)[1].split("## קריטריונים",1)[0]
        for prompt in ("משימות המשך","בחרו אחת מהשורות","איזו פעולה הופכת","כתבו הסבר מדויק לסיבוב","האם יש דרך נוספת"):
            self.assertIn(prompt,worksheet)
        abc=[(4,1),(7,1),(4,3)]
        ops={"DEF":quarter,"GHI":half,"JKL":flip_h,"MNP":lambda p:flip_v(p,1),
             "QRS":lambda p:move(p,-9,-9)}
        for code,op in ops.items():
            with self.subTest(image=code):
                images=[op(p) for p in abc]
                shown=", ".join(code[i]+show(p) for i,p in enumerate(images))
                self.assertIn(shown,section)
                self.assertEqual(area2(abc),area2(images))
        self.assertIn("**משימות המשך — תשובות למורה:**",section)
        for token in ("AB=DE=3","AC=DF=2","BC=EF=√13","JKL","MNP",
                      "כיווניות","O(0,0)","נגד כיוון השעון","(x,y)→(-x,-y)"):
            self.assertIn(token,section)
        self.assertEqual(squared(abc[0],abc[1]),9)
        self.assertEqual(squared(abc[0],abc[2]),4)
        self.assertEqual(squared(abc[1],abc[2]),13)
        def orientation(points):
            a,b,c=points
            return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        self.assertGreater(orientation(abc),0)
        self.assertLess(orientation([flip_h(p) for p in abc]),0)
        self.assertLess(orientation([flip_v(p,1) for p in abc]),0)
        self.assertGreater(orientation([quarter(p) for p in abc]),0)
        self.assertEqual([flip_v(flip_h(p)) for p in abc],[half(p) for p in abc])

if __name__=="__main__":
    unittest.main(verbosity=2)
