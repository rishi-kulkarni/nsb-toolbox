import unittest
from pathlib import Path

import pytest
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Pt
from nsb_toolbox import tables

data_dir = Path(__file__).parent / "test_data"


init_table_sizes = (0, 30, 60)
init_table_subj = (None, "Chemistry", "Earth and Space")
init_table_set = (None, "HSR", "MSN")
init_table_author = (None, "Rishi", "Andrew")


@pytest.fixture(
    scope="module",
    params=zip(init_table_sizes, init_table_subj, init_table_set, init_table_author),
    ids=["Empty", "30 Rows", "60 Rows"],
)
def initialize_params(request):
    return request.param


@pytest.fixture(scope="module")
def initialized_doc_with_table(initialize_params):
    nrows, subj, set_, name = initialize_params
    return tables.initialize_table(nrows, subj=subj, set=set_, name=name)


@pytest.fixture(scope="module")
def table_cells(initialized_doc_with_table):
    return initialized_doc_with_table.tables[0]._cells


class TestInitialize:
    def test_font_name(self, initialized_doc_with_table):
        assert (
            initialized_doc_with_table.styles["Normal"].font.name == "Times New Roman"
        )

    def test_font_size(self, initialized_doc_with_table):
        assert initialized_doc_with_table.styles["Normal"].font.size == Pt(11)

    def test_number_of_tables_in_doc(self, initialized_doc_with_table):
        assert len(initialized_doc_with_table.tables) == 1

    def test_numer_of_rows_in_table(
        self, initialized_doc_with_table, initialize_params
    ):
        generated_rows = len(initialized_doc_with_table.tables[0].rows)
        expected_rows = initialize_params[0]
        assert generated_rows == expected_rows + 1

    def test_cell_widths(self, table_cells):

        for idx, cell in enumerate(table_cells):
            row_idx, col_idx = divmod(idx, 13)

            assert pytest.approx(cell.width.inches, 0.001) == tables.COL_WIDTHS[col_idx]

    def test_cell_optional_parameters(self, table_cells, initialize_params):

        _, subj, set_, author = initialize_params

        for idx, cell in enumerate(table_cells):
            row_idx, col_idx = divmod(idx, 13)

            if col_idx == 1 and row_idx > 0 and subj:
                assert cell.text == subj

            if col_idx == 5 and row_idx > 0 and set_:
                assert cell.text == set_

            if col_idx == 8 and row_idx > 0 and author:
                assert cell.text == author


class TestFormatTUBCell(unittest.TestCase):

    test_data = Document(data_dir / "test_TUB.docx")

    def _check(self, formatted_cell, expected_text):
        self.assertEqual(formatted_cell.text, expected_text)

        self.assertEqual(len(formatted_cell.paragraphs), 1)

        cell_runs = formatted_cell.paragraphs[0].runs
        self.assertEqual(len(cell_runs), 1)
        self.assertIsNone(cell_runs[0].font.italic)
        self.assertIsNone(cell_runs[0].font.bold)

    def test_TUB(self):
        TUB = ("TOSS-UP", "BONUS", "VISUAL BONUS")
        test_rows = self.test_data.tables[0].rows[:3]

        for row, tub_expected in zip(test_rows, TUB):
            for cell in row.cells:
                tub_formatter = tables.TuBCellFormatter(cell)
                self._check(tub_formatter.format(), tub_expected)

    def test_errors(self):
        error_row = self.test_data.tables[0].rows[3]
        for cell in error_row.cells:
            prior_text = cell.text
            tub_formatter = tables.TuBCellFormatter(cell)
            test_run = tub_formatter.format().paragraphs[0].runs[0]
            after_text = cell.text
            self.assertEqual(prior_text, after_text)
            self.assertEqual(test_run.font.highlight_color, WD_COLOR_INDEX.RED)


class TestFormatSubject(unittest.TestCase):

    test_data = Document(data_dir / "test_subject.docx")

    def _check(self, formatted_cell, expected_text):
        self.assertEqual(formatted_cell.text, expected_text)

        self.assertEqual(len(formatted_cell.paragraphs), 1)

        cell_runs = formatted_cell.paragraphs[0].runs
        self.assertEqual(len(cell_runs), 1)
        self.assertIsNone(cell_runs[0].font.italic)
        self.assertIsNone(cell_runs[0].font.bold)

    def test_subject(self):
        SUBJECTS = (
            "Biology",
            "Chemistry",
            "Physics",
            "Earth and Space",
            "Math",
            "Energy",
        )

        test_rows = self.test_data.tables[0].rows[:6]

        for row, subject in zip(test_rows, SUBJECTS):
            for cell in row.cells:
                sformatter = tables.SubjectCellFormatter(cell)
                self._check(sformatter.format(), subject)

    def test_errors(self):
        error_row = self.test_data.tables[0].rows[6]
        for cell in error_row.cells:
            prior_text = cell.text
            sformatter = tables.SubjectCellFormatter(cell)
            test_run = sformatter.format().paragraphs[0].runs[0]
            after_text = cell.text
            self.assertEqual(prior_text, after_text)
            self.assertEqual(test_run.font.highlight_color, WD_COLOR_INDEX.RED)


class TestQuestionFormatter(unittest.TestCase):
    test_data = Document(data_dir / "test_question_parser.docx")

    def _extract_cell_text(self, cell):
        ret = []
        for para in cell.paragraphs:
            if para.runs == []:
                ret.append("")
            else:
                for run in para.runs:
                    ret.append(run.text)

        return ret

    def test_short_answer(self):
        """This makes sure that recognizable Short Answer questions
        are properly formatted."""
        expected = [
            "Short Answer",
            "    This is a well-formatted question.",
            "",
            "ANSWER: IT SHOULD BE UNCHANGED",
        ]

        cells = self.test_data.tables[0].rows[0].cells

        for cell in cells:
            q_parser = tables.QuestionCellFormatter(tables.preprocess_cell(cell))
            test_text = self._extract_cell_text(q_parser.format())
            self.assertEqual(test_text, expected)
            self.assertEqual(cell.paragraphs[-1].runs[0].font.highlight_color, None)

    def test_multiple_choice(self):
        """This makes sure that recognizable Multiple Choice questions
        are properly formatted."""
        expected = [
            "Multiple Choice",
            "    This is a well-formatted question.",
            "W) This is the W) choice",
            "X) This is the X) choice",
            "Y) This is the Y) choice",
            "Z) This is the Z) choice",
            "",
            "ANSWER: W) THIS IS THE W) CHOICE",
        ]

        cells = self.test_data.tables[0].rows[1].cells

        for cell in cells:
            q_parser = tables.QuestionCellFormatter(tables.preprocess_cell(cell))
            test_text = self._extract_cell_text(q_parser.format())
            self.assertEqual(test_text, expected)
            self.assertEqual(cell.paragraphs[-1].runs[0].font.highlight_color, None)

    def test_no_caps_multiple_choice(self):
        """This makes sure that Multiple Choice questions with a given answer
        don't have their answer auto-capitalized."""

        expected = [
            "Multiple Choice",
            "    This is a well-formatted question.",
            "W) This is the W) choice",
            "X) This is the X) choice",
            "Y) This is the Y) choice",
            "Z) This is the Z) choice",
            "",
            "ANSWER: W) this is the w) choice",
        ]

        cells = self.test_data.tables[0].rows[4].cells

        for cell in cells[:1]:
            q_parser = tables.QuestionCellFormatter(tables.preprocess_cell(cell))
            test_text = self._extract_cell_text(q_parser.format())
            self.assertEqual(test_text, expected)
            self.assertEqual(cell.paragraphs[-1].runs[0].font.highlight_color, None)

    def test_question_type_warning(self):
        """Tests that mislabeled question types get warnings."""
        cells = self.test_data.tables[0].rows[2].cells

        for cell in cells:
            q_parser = tables.QuestionCellFormatter(tables.preprocess_cell(cell))
            test_cell = q_parser.format()
            self.assertEqual(
                test_cell.paragraphs[0].runs[0].font.highlight_color,
                WD_COLOR_INDEX.YELLOW,
            )
            self.assertEqual(cell.paragraphs[-1].runs[0].font.highlight_color, None)

    def test_answer_line_warning(self):
        """Tests that answer lines that don't match choices in
        MC questions get warnings."""
        cells = self.test_data.tables[0].rows[3].cells

        for cell in cells:
            q_parser = tables.QuestionCellFormatter(tables.preprocess_cell(cell))
            test_cell = q_parser.format()
            self.assertEqual(
                test_cell.paragraphs[-1].runs[0].font.highlight_color,
                WD_COLOR_INDEX.YELLOW,
            )
