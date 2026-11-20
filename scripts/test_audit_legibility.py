#!/usr/bin/env python3
"""Regression test for Hebrew PDF glyph fragments in the figure legibility audit."""
import unittest
from audit_legibility import is_label


class PdfLabelClassification(unittest.TestCase):
    def test_punctuation_and_directionality_are_not_figure_labels(self):
        # These fragments appear as individual spans in the generated Noto Hebrew PDF.
        for fragment in ("\u200f", "\u200e", "\u2067", "״", "'", "?", "′"):
            with self.subTest(fragment=repr(fragment)):
                self.assertFalse(is_label(fragment))

    def test_real_vertex_and_axis_labels_still_count(self):
        for label in ("A", "H,", "A′", "P₁", "−4", "12", "ק", "y"):
            with self.subTest(label=label):
                self.assertTrue(is_label(label))


if __name__ == "__main__":
    unittest.main()
