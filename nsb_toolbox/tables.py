import re
from abc import ABC, abstractclassmethod
from enum import Enum
from functools import lru_cache, partial
from typing import Optional, Tuple

import docx.document
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Inches, Pt
from docx.table import _Cell, _Column
from docx.text.paragraph import Paragraph

from .classes import ErrorLogger, QuestionType, Subject, TossUpBonus
from .docx_utils import (
    clear_cell,
    column_indexer,
    copy_run_formatting,
    fuse_consecutive_runs,
    highlight_cell_text,
    highlight_paragraph_text,
    preprocess_cell,
    shade_columns,
    split_run_at,
)

COL_WIDTHS = (
    0.72,
    0.61,
    4.71,
    0.58,
    0.68,
    0.68,
    0.68,
    0.68,
    0.81,
    0.64,
    4.71,
    1.51,
    1.44,
)

COL_MAPPING = {
    "TUB": 0,
    "Subj": 1,
    "Ques": 2,
    "LOD": 3,
    "LOD-A": 4,
    "Set": 5,
    "Rd": 6,
    "Q Letter": 7,
    "Author": 8,
    "ID": 9,
    "Source": 10,
    "Comments": 11,
    "Subcat": 12,
}


class QuestionFormatterState(Enum):
    Q_START = 0
    STEM_END = 1
    CHOICES = 2
    ANSWER = 3


class CellFormatter(ABC):
    """Helper class that ensures formatters are standardized."""

    @abstractclassmethod
    def __init__(self, cell: _Cell, error_logger: Optional[ErrorLogger] = None):
        """All CellFormatters take the same input arguments."""

    @abstractclassmethod
    def format(self):
        """All CellFormatters have a format function."""


def make_jans_shadings(table):
    """Shades the 4, 6, 7, and 8th cells in a row the appropriate colors.

    Parameters
    ----------
    row : Document.rows object
    """
    shade_columns(table.columns[3], "#FFCC99")
    shade_columns(table.columns[5], "#e5dfec")
    shade_columns(table.columns[6], "#daeef3")
    shade_columns(table.columns[7], "#daeef3")


def initialize_table(
    nrows=0,
    name: Optional[str] = None,
    subj: Optional[str] = None,
    set: Optional[str] = None,
    path: Optional[str] = None,
) -> Document:
    """Initializes a docx file containing the Science Bowl header row.

    Parameters
    ----------
    nrows : int, optional
        Number of extra rows to append to the table, by default 0

    name : str, optional
        Name of author. If not none, fills the author column of the table.

    subj: str, optional
        Subject. If not none, fills the subject column of the table.

    set: str, optional
        Set. If not none, fills the set column of the table.

    path : Optional[str], optional
        Path that the docx file should be saved to.
        If None, merely returns the document, by default None

    Returns
    -------
    Document
    """
    document = Document()
    font = document.styles["Normal"].font
    font.name = "Times New Roman"
    font.size = Pt(11)

    table = document.add_table(rows=1 + nrows, cols=13)

    table.style = "Table Grid"
    table.autofit = False
    table.allow_autofit = False

    _cells = table._cells
    _col_count = table._column_count

    col_iter = partial(
        column_indexer, total_cells=len(_cells), col_count=_col_count, skip_header=True
    )

    for col_name, col_idx in COL_MAPPING.items():
        # add header
        table.cell(0, col_idx).paragraphs[0].add_run(col_name)
        table.cell(0, col_idx).width = Inches(COL_WIDTHS[col_idx])

        for cell_idx in col_iter(col_idx):
            cell = _cells[cell_idx]
            cell.width = Inches(COL_WIDTHS[col_idx])

            if col_name == "Subj" and subj is not None:
                cell.paragraphs[0].text = subj
            elif col_name == "Set" and set is not None:
                cell.paragraphs[0].text = set
            elif col_name == "Author" and name is not None:
                cell.paragraphs[0].text = name

    # ques header is italicized
    ques_run = table.cell(0, COL_MAPPING["Ques"]).paragraphs[0].runs[0]
    ques_run.italic = True

    make_jans_shadings(table)

    if path is not None:
        document.save(path)

    return document


@lru_cache
def _compile(regex: str):
    return re.compile(regex, re.IGNORECASE)


class QuestionCellFormatter(CellFormatter):
    """Formats a cell containing a Science Bowl Question."""

    _q_type_possible = _compile(r"\s*(Short Answer|SA|Multiple Choice|MC)\s*")
    _choices_re = _compile(r"\s*([W|X|Y|Z]\))\s*")
    _answer_re = _compile(r"\s*(ANSWER:)\s*")

    _choices = ("W)", "X)", "Y)", "Z)")

    def __init__(self, cell: _Cell, error_logger: Optional[ErrorLogger] = None):
        self.error_logger = error_logger
        self.cell = cell
        self.state = QuestionFormatterState.Q_START
        self.q_type = None
        self.q_type_run = None
        self.current_choice = 0
        self.choices_para = {}
        self.found_all = False
        self.errors = []

    def _start_handler(self, para: Paragraph):
        q_type_match = self._q_type_possible.match(para.text)
        if q_type_match:
            # the first run of the paragraph should contain the question start
            q_type_run = para.runs[0]
            run_match = self._q_type_possible.match(q_type_run.text)

            if run_match:
                self.q_type = QuestionType.from_string(run_match.group(1))
                # if the run contains more than the question type, split
                # the run into two
                if run_match.span()[1] < len(q_type_run.text):
                    q_type_run, _ = split_run_at(para, q_type_run, run_match.span()[1])

                q_type_run.text = self.q_type.value
                q_type_run.italic = True
                self.q_type_run = q_type_run

            else:
                # unfortunately, if someone has italicized a single
                # letter in the question start or something, we
                # will have a problem. in this case, highlight
                # the question.
                highlight_cell_text(self.cell, WD_COLOR_INDEX.RED)
                if self.error_logger is not None:
                    self.error_logger.log_error("Couldn't parse question.")
                return None

            # now, the first part of the stem is the second run
            # if it's not left-padded with 4 spaces, make sure it is
            # doing it this way ensures that any other formatting in
            # the stem is preserved (superscripts, subscripts, etc.)
            stem_run = para.runs[1]
            stem_run.text = f"    {stem_run.text.lstrip()}"

            self.state = QuestionFormatterState.STEM_END
        else:
            pass

    def _choice_handler(self, para: Paragraph):

        choice_match = self._choices_re.match(para.text)

        if choice_match:

            # the first run should contain the choice
            choice_run = para.runs[0]
            run_match = self._choices_re.match(choice_run.text)
            if run_match:
                # if we matched the wrong choice, replace it with
                # the right choice
                if run_match.group(1) != self._choices[self.current_choice]:
                    choice_run.text = choice_run.text.replace(
                        run_match.group(1), self._choices[self.current_choice], 1
                    )
                # save text and update the choice we're looking for
                self.choices_para[self.current_choice] = para
                self.current_choice += 1
            else:
                # same problem as above, it is possible that someone
                # italicized half of the choice start.
                highlight_cell_text(self.cell, WD_COLOR_INDEX.RED)
                if self.error_logger is not None:
                    self.error_logger.log_error("Couldn't parse question.")
                return None

            # if we just found Z), we're done looking for choices
            if self.current_choice == 4:
                self.current_choice = 0
                self.state = QuestionFormatterState.ANSWER

    def _answer_handler(self, para: Paragraph):
        # if we find a choice line while looking for an answer,
        # the question is probably not Short Answer. highlight
        # the question type to indicate this

        answer_match = self._answer_re.match(para.text)
        if answer_match:
            para.insert_paragraph_before("")

            # for MC questions, additional checks to make sure
            # answer line matches choice
            if self.q_type is QuestionType.MULTIPLE_CHOICE:
                answer_text = para.text.replace("ANSWER: ", "", 1)

                test_choice_re = _compile(r"\s*([W|X|Y|Z]\)?)\s*")
                test_choice_match = test_choice_re.match(answer_text)
                if test_choice_match:
                    # if answer line is a single letter, copy the text of
                    # the choice over to the answer line
                    if test_choice_match.span()[1] == len(answer_text):
                        test_choice = test_choice_match.group(1)
                        if not test_choice.endswith(")"):
                            test_choice += ")"
                        correct_para = self.choices_para[
                            self._choices.index(test_choice)
                        ]
                        para.text = "ANSWER: "
                        for run in correct_para.runs:
                            new_run = para.add_run(run.text.upper())
                            copy_run_formatting(run, new_run)
                        fuse_consecutive_runs(para)
                    # otherwise, check that the answer line text matches the choice.
                    # if it doesn't raise a linting error.
                    else:
                        choice_num = self._choices.index(test_choice_match.group(1))
                        if (
                            self.choices_para[choice_num].text.upper()
                            != answer_text.upper()
                        ):
                            highlight_paragraph_text(para, WD_COLOR_INDEX.YELLOW)
                            if self.error_logger is not None:
                                self.error_logger.log_error(
                                    "Answer line doesn't match choice."
                                )

            # if we made it here, we found everything.
            self.found_all = True

    def format(self):
        """Takes a preprocessed question cell
        and returns a cell containing a properly-formatted
        Science Bowl question.

        Returns
        -------
        _Cell
        """
        for para in self.cell.paragraphs:

            if self.state is QuestionFormatterState.Q_START:
                self._start_handler(para)

            elif self.state is QuestionFormatterState.STEM_END:
                choice_match = self._choices_re.match(para.text)
                answer_match = self._answer_re.match(para.text)

                if choice_match:
                    if self.q_type is QuestionType.SHORT_ANSWER:
                        self.q_type_run.font.highlight_color = WD_COLOR_INDEX.YELLOW
                        if self.error_logger is not None:
                            self.error_logger.log_error(
                                "Question type is SA, but has choices."
                            )
                        self.q_type = QuestionType.MULTIPLE_CHOICE
                    self.state = QuestionFormatterState.CHOICES
                    self._choice_handler(para)

                elif answer_match:
                    if self.q_type is QuestionType.MULTIPLE_CHOICE:
                        self.q_type_run.font.highlight_color = WD_COLOR_INDEX.YELLOW
                        if self.error_logger is not None:
                            self.error_logger.log_error(
                                "Question type is MC, but has no choices."
                            )
                        self.q_type = QuestionType.SHORT_ANSWER
                    self.state = QuestionFormatterState.ANSWER
                    self._answer_handler(para)

            elif self.state is QuestionFormatterState.CHOICES:

                self._choice_handler(para)

            elif self.state is QuestionFormatterState.ANSWER:

                self._answer_handler(para)

        if not self.found_all:
            # if we get through the entire cell without finding all parts of
            # of the question, highlight the cell red
            highlight_cell_text(self.cell, WD_COLOR_INDEX.RED)
            if self.error_logger is not None:
                self.error_logger.log_error(
                    f"Couldn't parse question, was looking for {self.state}"
                )
        else:
            if self.error_logger is not None:
                self.error_logger.stats[self.q_type.value] += 1

        return self.cell


class TuBCellFormatter(CellFormatter):
    tub_possible = _compile(r"\s*(TOSS-UP|BONUS|VISUAL BONUS|TU|B|VB)\b")

    def __init__(self, cell: _Cell, error_logger: Optional[ErrorLogger] = None):
        self.cell = cell
        self.error_logger = error_logger

    def format(self) -> _Cell:
        tub_match = self.tub_possible.match(self.cell.text)

        if tub_match:
            put = TossUpBonus.from_string(tub_match.group(1)).value
            clear_cell(self.cell)
            tub_run = self.cell.paragraphs[0].runs[0]
            tub_run.text = put
            tub_run.italic = None
            tub_run.bold = None
            highlight_cell_text(self.cell, None)

            if self.error_logger is not None:
                self.error_logger.stats[put] += 1

        # if a match can't be found, highlight the cell red
        else:
            highlight_cell_text(self.cell, WD_COLOR_INDEX.RED)
            if self.error_logger is not None:
                self.error_logger.log_error(
                    "Question must be a toss-up, bonus, or visual bonus."
                )

        return self.cell


class SubjectCellFormatter(CellFormatter):
    subject_possible = _compile(
        r"\s*(BIOLOGY|B|CHEMISTRY|C|EARTH AND SPACE|ES|ENERGY|EN|MATH|M|PHYSICS|P)\b"
    )

    def __init__(self, cell: _Cell, error_logger: Optional[ErrorLogger] = None):
        self.cell = cell
        self.error_logger = error_logger

    def format(self):

        subject_match = self.subject_possible.match(self.cell.text)

        if subject_match:
            put = Subject.from_string(subject_match.group(1)).value
            clear_cell(self.cell)
            subj_run = self.cell.paragraphs[0].runs[0]
            subj_run.text = put
            subj_run.italic = None
            subj_run.bold = None
            highlight_cell_text(self.cell, None)
        # if a match can't be found, highlight the cell red
        else:
            highlight_cell_text(self.cell, WD_COLOR_INDEX.RED)
            if self.error_logger is not None:
                self.error_logger.log_error("Invalid subject.")

        return self.cell


class DifficultyFormatter(CellFormatter):
    def __init__(self, cell: _Cell, error_logger: Optional[ErrorLogger] = None):
        self.cell = cell
        self.error_logger = error_logger

    def format(self):

        if self.cell.text:
            try:
                int(self.cell.text)
            except ValueError:
                highlight_cell_text(self.cell, WD_COLOR_INDEX.RED)
                if self.error_logger is not None:
                    self.error_logger.log_error("LOD should be blank or an integer.")

        return self.cell


def format_column(
    nsb_table_column: _Column,
    formatter: Optional[CellFormatter],
    error_logger: Optional[ErrorLogger] = None,
) -> _Column:
    """Utility function that applies a formatter to every cell in a column.

    Parameters
    ----------
    nsb_table_column : _Column
    formatter : CellFormatter instance
    error_logger : Optional[ErrorLogger], optional

    Returns
    -------
    _Column
    """
    for idx, cell in enumerate(nsb_table_column):
        cell = preprocess_cell(cell)
        if error_logger is not None:
            error_logger.set_row(idx + 1)
        if cell.text.strip() != "" and formatter:
            formatter(cell, error_logger).format()
    return nsb_table_column


def format_table(
    table_doc: docx.document.Document, cols_to_format: Tuple[str], verbosity=True
):
    """Formats a Word document containing a Science Bowl question table.

    Specifically, this function makes sure the columns fit the following
    criteria:

    TUB: Contains only TOSS-UP or BONUS
    Subj: Contains only one of the valid subject areas
    Ques: Contains a properly-formatted Short Answer or Multiple Choice question
    LOD: Contains only an integer or is blank.
    Set: Contains no extra whitespace
    Author: Contains no extra whitespace
    Subcat: Contains no extra whitespace

    Parameters
    ----------
    table_doc : Document
    verbosity : bool, default True
    """
    FORMATTERS = {
        "TUB": TuBCellFormatter,
        "Subj": SubjectCellFormatter,
        "Ques": QuestionCellFormatter,
        "LOD": DifficultyFormatter,
    }
    error_logger = ErrorLogger(verbosity)

    _cells = table_doc.tables[0]._cells
    _col_count = table_doc.tables[0]._column_count

    col_iter = partial(
        column_indexer, total_cells=len(_cells), col_count=_col_count, skip_header=True
    )

    for col_name in cols_to_format:
        format_column(
            [_cells[i] for i in col_iter(COL_MAPPING[col_name])],
            FORMATTERS.get(col_name, None),
            error_logger,
        )

    if len(error_logger.errors) == 0:
        print("Found no errors 😄")
    print(error_logger)
