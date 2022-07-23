import unittest
from pathlib import Path

import pytest
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Pt
from nsb_toolbox import tables
from nsb_toolbox.classes import ErrorLogger

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


@pytest.fixture
def tub_test_doc():
    return Document(data_dir / "test_TUB.docx")


@pytest.mark.parametrize("error_logger", [None, ErrorLogger(verbosity=True)])
@pytest.mark.parametrize("row_idx", [0, 1, 2], ids=["TOSS-UP", "BONUS", "VISUAL BONUS"])
class TestTUBCellFormatter:
    def test_formatted_text(self, tub_test_doc, row_idx, error_logger):
        expected_text = ["TOSS-UP", "BONUS", "VISUAL BONUS"]
        row = tub_test_doc.tables[0].rows[row_idx]
        for cell in row.cells:
            formatted_cell = tables.TuBCellFormatter(cell, error_logger).format()
            assert formatted_cell.text == expected_text[row_idx]

    def test_cell_has_single_paragraph(self, tub_test_doc, row_idx, error_logger):
        row = tub_test_doc.tables[0].rows[row_idx]
        for cell in row.cells:
            formatted_cell = tables.TuBCellFormatter(cell, error_logger).format()
            assert len(formatted_cell.paragraphs) == 1

    def test_paragraph_contains_one_run_with_normal_text(
        self, tub_test_doc, row_idx, error_logger
    ):
        row = tub_test_doc.tables[0].rows[row_idx]
        for cell in row.cells:
            formatted_cell = tables.TuBCellFormatter(cell, error_logger).format()
            cell_runs = formatted_cell.paragraphs[0].runs
            assert len(cell_runs) == 1
            assert cell_runs[0].font.italic is None
            assert cell_runs[0].font.bold is None


@pytest.mark.parametrize("error_logger", [None, ErrorLogger(verbosity=True)])
class TestTUBCellFormatterErrors:
    def test_unrecognizable_cell_text_is_unchanged(self, tub_test_doc, error_logger):
        row = tub_test_doc.tables[0].rows[3]
        for cell in row.cells:
            prior_text = cell.text
            formatted_cell = tables.TuBCellFormatter(cell, error_logger).format()
            after_text = formatted_cell.text
            assert prior_text == after_text
            if error_logger:
                assert len(error_logger.errors) > 0

    def test_unrecognizable_cell_is_highlighted(self, tub_test_doc, error_logger):
        row = tub_test_doc.tables[0].rows[3]
        for cell in row.cells:
            formatted_cell = tables.TuBCellFormatter(cell, error_logger).format()
            run = formatted_cell.paragraphs[0].runs[0]
            assert run.font.highlight_color == WD_COLOR_INDEX.RED
            if error_logger:
                assert len(error_logger.errors) > 0


@pytest.fixture
def format_subject_rows():
    test_data = Document(data_dir / "test_subject.docx")
    return test_data.tables[0].rows


@pytest.mark.parametrize(
    "row_idx",
    [0, 1, 2, 3, 4, 5],
    ids=[
        "Biology",
        "Chemistry",
        "Physics",
        "Earth and Space",
        "Math",
        "Energy",
    ],
)
@pytest.mark.parametrize(
    "cell_idx",
    [0, 1, 2, 3],
    ids=[
        "Full Correct",
        "Abbreviated",
        "Abbreviated Wrong Format",
        "Full Wrong Format",
    ],
)
class TestFormatSubject:
    def test_expected_text(self, format_subject_rows, row_idx, cell_idx):
        EXPECTED_TEXT = (
            "Biology",
            "Chemistry",
            "Physics",
            "Earth and Space",
            "Math",
            "Energy",
        )
        cell = format_subject_rows[row_idx].cells[cell_idx]
        formatter = tables.SubjectCellFormatter(cell)
        assert formatter.format().text == EXPECTED_TEXT[row_idx]

    def test_cell_formatting(self, format_subject_rows, row_idx, cell_idx):
        cell = format_subject_rows[row_idx].cells[cell_idx]
        formatter = tables.SubjectCellFormatter(cell)

        formatted_cell = formatter.format()
        assert len(formatted_cell.paragraphs) == 1
        assert len(formatted_cell.paragraphs[0].runs) == 1
        assert formatted_cell.paragraphs[0].runs[0].font.italic is None
        assert formatted_cell.paragraphs[0].runs[0].font.bold is None


@pytest.mark.parametrize(
    "cell_idx",
    [0, 1, 2, 3],
    ids=[
        "Biologychemistry",
        "Multiple Choice",
        "_Life Science_",
        "_Physical Science_",
    ],
)
class TestFormatSubjectErrors:
    def test_errors(self, format_subject_rows, cell_idx):
        cell = format_subject_rows[6].cells[cell_idx]

        prior_text = cell.text
        sformatter = tables.SubjectCellFormatter(cell)
        test_run = sformatter.format().paragraphs[0].runs[0]
        after_text = cell.text
        assert prior_text == after_text
        assert test_run.font.highlight_color == WD_COLOR_INDEX.RED


class TestQuestionFormatter(unittest.TestCase):
    test_data = Document(data_dir / "test_question_parser.docx")

    def _extract_cell_text(self, cell):
        ret = []
        for para in cell.paragraphs:
            if para.runs == []:
                ret.append([""])
            else:
                ret.append([run.text for run in para.runs])

        return ret

    def test_short_answer(self):
        """This makes sure that recognizable Short Answer questions
        are properly formatted."""
        expected = [
            ["Short Answer", "    This is a well-formatted question."],
            [""],
            ["ANSWER: IT SHOULD BE UNCHANGED"],
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
            ["Multiple Choice", "    This is a well-formatted question."],
            ["W) This is the W) choice"],
            ["X) This is the X) choice"],
            ["Y) This is the Y) choice"],
            ["Z) This is the Z) choice"],
            [""],
            ["ANSWER: W) THIS IS THE W) CHOICE"],
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
            ["Multiple Choice", "    This is a well-formatted question."],
            ["W) This is the W) choice"],
            ["X) This is the X) choice"],
            ["Y) This is the Y) choice"],
            ["Z) This is the Z) choice"],
            [""],
            ["ANSWER: W) this is the w) choice"],
        ]

        cells = self.test_data.tables[0].rows[4].cells

        for cell in cells[:1]:
            q_parser = tables.QuestionCellFormatter(tables.preprocess_cell(cell))
            test_text = self._extract_cell_text(q_parser.format())
            self.assertEqual(test_text, expected)
            self.assertEqual(cell.paragraphs[-1].runs[0].font.highlight_color, None)

    def test_force_capitalize_multiple_choice(self):
        """This makes sure that forced capitalization works on
        Multiple Choice questions."""

        expected = [
            ["Multiple Choice", "    This is a well-formatted question."],
            ["W) This is the W) choice"],
            ["X) This is the X) choice"],
            ["Y) This is the Y) choice"],
            ["Z) This is the Z) choice"],
            [""],
            ["ANSWER: W) THIS IS THE W) CHOICE"],
        ]

        cells = self.test_data.tables[0].rows[5].cells

        for cell in cells[:1]:
            q_parser = tables.QuestionCellFormatter(
                tables.preprocess_cell(cell), force_capitalize=True
            )
            test_text = self._extract_cell_text(q_parser.format())
            self.assertEqual(test_text, expected)
            self.assertEqual(cell.paragraphs[-1].runs[0].font.highlight_color, None)

    def test_force_capitalize_short_answer(self):
        """This makes sure that forced capitalization works on
        Short Answer questions."""

        expected = [
            ["Short Answer", "    This is a well-formatted question."],
            [""],
            ["ANSWER: IT SHOULD BE UNCHANGED"],
        ]

        cells = self.test_data.tables[0].rows[6].cells

        for cell in cells[:1]:
            q_parser = tables.QuestionCellFormatter(
                tables.preprocess_cell(cell), force_capitalize=True
            )
            test_text = self._extract_cell_text(q_parser.format())
            self.assertEqual(test_text, expected)
            self.assertEqual(cell.paragraphs[-1].runs[0].font.highlight_color, None)

    def test_line_break_short_answer(self):
        """This makes sure that SA questions with a line break between the question type
        and the stem are handled properly."""

        expected = [
            ["Short Answer", "    This is a well-formatted question."],
            [""],
            ["ANSWER: IT SHOULD BE UNCHANGED"],
        ]

        cells = self.test_data.tables[0].rows[7].cells

        for cell in cells[:1]:
            q_parser = tables.QuestionCellFormatter(
                tables.preprocess_cell(cell),
            )
            test_text = self._extract_cell_text(q_parser.format())
            self.assertEqual(test_text, expected)
            self.assertEqual(cell.paragraphs[-1].runs[0].font.highlight_color, None)

    def test_line_break_multiple_choice(self):
        """This makes sure that MC questions with a line break between the question type
        and the stem are handled properly."""

        expected = [
            ["Multiple Choice", "    This is a well-formatted question."],
            ["W) This is the W) choice"],
            ["X) This is the X) choice"],
            ["Y) This is the Y) choice"],
            ["Z) This is the Z) choice"],
            [""],
            ["ANSWER: W) THIS IS THE W) CHOICE"],
        ]

        cells = self.test_data.tables[0].rows[8].cells

        for cell in cells[:1]:
            q_parser = tables.QuestionCellFormatter(
                tables.preprocess_cell(cell),
            )
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
