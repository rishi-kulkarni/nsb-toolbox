from pathlib import Path
from unittest import TestCase

import numpy as np
from numpy.testing import assert_equal

from nsb_toolbox.assign import EditedQuestions, ParsedQuestionSpec

from nsb_toolbox.importers import load_doc, load_yaml

data_dir = Path(__file__).parent / "test_data"


class TestEditedQuestions(TestCase):
    def setUp(self):
        test_doc = load_doc(data_dir / "test_assign_questions.docx")
        self.instance = EditedQuestions(test_doc)

    def test_tub_field(self):
        expected_tub = np.array(["TOSS-UP"] * 5 + ["BONUS"] * 5)
        assert_equal(self.instance.tubs, expected_tub)

    def test_set_field(self):

        expected_sets = ["HSR-A", "HSR-B", "HSR", "HSR", "HSR"] * 2
        self.assertEqual([x.text for x in self.instance.sets], expected_sets)

    def test_diff_field(self):

        expected_difficulties = np.array([1, 2, 3, 3, 3, 1, 2, 3, 4, 2])
        assert_equal(self.instance.difficulties, expected_difficulties)

    def test_qtypes_field(self):
        expected_qtypes = np.array(
            ["Multiple Choice"] * 3 + ["Short Answer"] * 6 + ["Multiple Choice"]
        )
        assert_equal(self.instance.qtypes, expected_qtypes)

    def test_subcat_field(self):

        expected_subcategories = np.array([""] * 3 + ["Organic"] * 4 + [""] * 3)
        assert_equal(self.instance.subcategories, expected_subcategories)

    def test_rounds_field(self):

        expected_rounds = [""] * 10
        self.assertEqual([x.text for x in self.instance.rounds], expected_rounds)

    def test_qletter_field(self):

        expected_qletters = [""] * 10
        self.assertEqual([x.text for x in self.instance.qletters], expected_qletters)

    def test_invalid_tubs(self):

        test_doc = load_doc(data_dir / "test_assign_questions.docx")
        test_doc.tables[0].column_cells(0)[1].text = "Invalid TUB"

        with self.assertRaisesRegex(
            ValueError, "One or more issues with the question document"
        ):
            EditedQuestions(test_doc)

    def test_invalid_diff(self):

        test_doc = load_doc(data_dir / "test_assign_questions.docx")
        test_doc.tables[0].column_cells(3)[1].text = "Invalid LOD"

        with self.assertRaisesRegex(
            ValueError, "One or more issues with the question document"
        ):
            EditedQuestions(test_doc)

    def test_invalid_ques(self):

        test_doc = load_doc(data_dir / "test_assign_questions.docx")
        test_doc.tables[0].column_cells(2)[1].text = "Invalid Ques"

        with self.assertRaisesRegex(
            ValueError, "One or more issues with the question document"
        ):
            EditedQuestions(test_doc)

    def test_prefilled_rd_set(self):

        test_doc = load_doc(data_dir / "test_assign_questions.docx")
        test_doc.tables[0].column_cells(6)[1].text = "RR1"

        with self.assertRaisesRegex(
            ValueError, "The Round and Q Letter columns are not empty in this document"
        ):
            EditedQuestions(test_doc)


class TestParsedQuestionSpec(TestCase):
    def setUp(self):
        self.instance = ParsedQuestionSpec(
            load_yaml(data_dir / "test_assign_config.yaml")
        )

    def test_tubs_field(self):
        expected = np.array(
            [
                "TOSS-UP",
                "TOSS-UP",
                "BONUS",
                "BONUS",
                "TOSS-UP",
                "TOSS-UP",
                "BONUS",
                "BONUS",
            ],
            dtype="<U20",
        )
        assert_equal(self.instance.tubs, expected)

    def test_diff_field(self):
        expected = np.array([1, 2, 1, 3, 1, 2, 1, 3])
        assert_equal(self.instance.difficulties, expected)

    def test_qtypes_field(self):
        expected = np.array(["", "Short Answer"] * 4)
        assert_equal(self.instance.qtypes, expected)

    def test_subcat_field(self):
        expected = np.array(["Organic", ""] * 4)
        assert_equal(self.instance.subcategories, expected)

    def test_sets_field(self):
        expected = np.array(["HSR-A"] * 4 + ["HSR-B"] * 4)
        assert_equal(self.instance.sets, expected)

    def test_rounds_field(self):
        expected = np.array(["RR1"] * 8)
        assert_equal(self.instance.rounds, expected)

    def test_qletters_field(self):
        expected = np.array(["A", "B"] * 4)
        assert_equal(self.instance.qletters, expected)
