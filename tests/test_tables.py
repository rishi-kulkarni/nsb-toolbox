import unittest
from pathlib import Path

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Pt
from nsb_toolbox import tables

data_dir = Path(__file__).parent / "test_data"


class TestInitializeTable(unittest.TestCase):
    def _check_table_characteristics(self, document, nrows):

        font = document.styles["Normal"].font
        self.assertEqual(font.name, "Times New Roman")
        self.assertEqual(font.size, Pt(11))

        self.assertEqual(len(document.tables), 1)
        table = document.tables[0]
        self.assertEqual(len(table.rows), nrows + 1)

        for idx, cell in enumerate(table.rows[0].cells):
            self.assertAlmostEqual(cell.width.inches, tables.COL_WIDTHS[idx], places=2)

    def test_intialize_table(self):
        _nrows = (0, 90, 150, 180)
        for nrow in _nrows:
            document = tables.initialize_table(nrow)
            self._check_table_characteristics(document, nrow)


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
