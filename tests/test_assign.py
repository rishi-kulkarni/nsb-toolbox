from pathlib import Path
from unittest import TestCase
from nsb_toolbox.assign import EditedQuestions

from nsb_toolbox.importers import load_doc

data_dir = Path(__file__).parent / "test_data"


class TestEditedQuestions(TestCase):
    def setUp(self):
        test_doc = load_doc(data_dir / "test_assign_questions.docx")
        self.instance = EditedQuestions(test_doc)

    def test_tub_field(self):
        expected_tub = ["TOSS-UP"] * 5 + ["BONUS"] * 5
        self.assertEqual([x.value for x in self.instance.tubs], expected_tub)

    def test_set_field(self):

        expected_sets = ["HSR-A", "HSR-B", "HSR", "HSR", "HSR"] * 2
        self.assertEqual([x.text for x in self.instance.sets], expected_sets)

    def test_diff_field(self):

        expected_difficulties = [1, 2, 3, 3, 3, 1, 2, 3, 4, 2]
        self.assertEqual(self.instance.difficulties, expected_difficulties)

    def test_qtypes_field(self):
        expected_qtypes = (
            ["Multiple Choice"] * 3 + ["Short Answer"] * 6 + ["Multiple Choice"]
        )
        self.assertEqual([x.value for x in self.instance.qtypes], expected_qtypes)

    def test_subcat_field(self):

        expected_subcategories = [""] * 3 + ["Organic"] * 4 + [""] * 3
        self.assertEqual(self.instance.subcategories, expected_subcategories)

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
