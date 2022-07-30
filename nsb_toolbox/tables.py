import re
from copy import deepcopy
from enum import Enum
from functools import partial
from typing import Dict, Iterable, Optional, Tuple, Union

import docx.document
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Inches, Pt
from docx.table import _Cell
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from .classes import ErrorLogger, QuestionType, Subject, TossUpBonus
from .docx_utils import (
    capitalize_paragraph,
    clear_cell,
    column_indexer,
    fuse_consecutive_runs,
    highlight_cell_text,
    highlight_paragraph_text,
    move_runs_to_end_of_para,
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

TUB_RE = re.compile(r"\s*(TOSS-UP|BONUS|VISUAL BONUS|TU|B|VB)\b", re.IGNORECASE)
SUBJECT_RE = re.compile(
    r"\s*(BIOLOGY|B|CHEMISTRY|C|EARTH AND SPACE|ES|ENERGY|EN|MATH|M|PHYSICS|P)\b",
    re.IGNORECASE,
)
Q_TYPE_RE = re.compile(r"\s*(Short Answer|SA|Multiple Choice|MC)\s*", re.IGNORECASE)
CHOICES_RE = re.compile(r"\s*([W|X|Y|Z]\))\s*", re.IGNORECASE)
TEST_CHOICE_RE = re.compile(r"(?:ANSWER:)?\s*([W|X|Y|Z])(?:\)?$|\).+)", re.IGNORECASE)
ANSWER_RE = re.compile(r"\s*(ANSWER:)\s*", re.IGNORECASE)

CHOICES = ("W)", "X)", "Y)", "Z)")


class QuestionFormatterState(Enum):
    Q_START = 0
    STEM_END = 1
    CHOICES = 2
    ANSWER = 3
    DONE = 4


class CellFormatter:
    """Base class that ensures formatters are standardized."""

    def __init__(self, error_logger: Optional[ErrorLogger] = None):
        self.error_logger = error_logger

    def format(self, cell: _Cell) -> _Cell:
        """All CellFormatters have a format function."""
        return cell

    def preprocess_format(self, cell: _Cell) -> _Cell:
        """Convenience function to preprocess and format a cell."""
        cell = preprocess_cell(cell)
        if cell.text.strip() != "":
            return self.format(cell)

    def preprocess_format_column(self, cells: Iterable[_Cell]) -> _Cell:
        """Convenience function to preprocess and format an entire column."""
        for idx, cell in enumerate(cells):
            if self.error_logger is not None:
                self.error_logger.set_row(idx + 1)
            self.preprocess_format(cell)

    def log_error(self, msg: str, cell: _Cell, level: int = 0):
        if level == 1:
            highlight_cell_text(cell, WD_COLOR_INDEX.YELLOW)
        elif level == 2:
            highlight_cell_text(cell, WD_COLOR_INDEX.RED)
        if self.error_logger is not None:
            self.error_logger.log_error(msg)


def format_table(
    table_doc: docx.document.Document,
    cols_to_format: Tuple[str],
    force_capitalize: bool = False,
    verbosity: bool = True,
) -> None:
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

    error_logger = ErrorLogger(verbosity)

    FORMATTERS = {
        "TUB": TuBCellFormatter(error_logger),
        "Subj": SubjectCellFormatter(error_logger),
        "Ques": QuestionCellFormatter(
            force_capitalize=force_capitalize, error_logger=error_logger
        ),
        "LOD": DifficultyFormatter(error_logger),
    }

    _cells = table_doc.tables[0]._cells
    _col_count = table_doc.tables[0]._column_count

    col_iter = partial(
        column_indexer, total_cells=len(_cells), col_count=_col_count, skip_header=True
    )

    for col_name in cols_to_format:
        formatter = FORMATTERS.get(col_name, CellFormatter(error_logger))
        formatter.preprocess_format_column(
            _cells[i] for i in col_iter(COL_MAPPING[col_name])
        )

    if len(error_logger.errors) == 0:
        print("Found no errors 😄")
    print(error_logger)


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


class QuestionParserException(Exception):
    pass


class QuestionCellFormatter(CellFormatter):
    """Formats a cell containing a Science Bowl Question."""

    def __init__(
        self,
        force_capitalize: bool = False,
        error_logger: Optional[ErrorLogger] = None,
    ):
        super().__init__(error_logger)
        self.force_capitalize = force_capitalize

    def format(self, cell: _Cell) -> _Cell:
        """Takes a preprocessed question cell and returns a cell containing a
        properly-formatted Science Bowl question.

        Parameters
        ----------
        cell : _Cell

        Returns
        -------
        _Cell
            Cell containing a formatteed Science Bowl question.
        """

        state = QuestionFormatterState.Q_START
        q_type = None
        q_type_run = None
        current_choice = 0
        choices_para = {}

        for para in cell.paragraphs:

            if state is QuestionFormatterState.DONE:
                break

            elif state is QuestionFormatterState.Q_START and Q_TYPE_RE.match(para.text):

                try:
                    run_match = _validate_element_text(
                        q_type_run := para.runs[0], pattern=Q_TYPE_RE
                    )
                except QuestionParserException as ex:
                    self.log_error(str(ex), cell, level=2)
                    break

                q_type = _format_question_type_run(q_type_run, run_match)

                if len(para.runs) == 1:
                    try:
                        _combine_qtype_and_stem_paragraphs(para)
                    except QuestionParserException as ex:
                        self.log_error(str(ex), cell, level=2)
                        break

                # left pad the first run of the stem
                _left_pad_stem(stem_run=para.runs[1])

                state = QuestionFormatterState.STEM_END

            elif state is QuestionFormatterState.STEM_END:
                # handle incorrectly labeled questions and divert to the proper state
                if CHOICES_RE.match(para.text):
                    if q_type is QuestionType.SHORT_ANSWER:
                        self.log_error("Question type is SA, but has choices.", cell)
                        q_type = _toggle_q_type_and_warn(q_type, q_type_run)
                    state = QuestionFormatterState.CHOICES

                elif ANSWER_RE.match(para.text):
                    if q_type is QuestionType.MULTIPLE_CHOICE:
                        self.log_error("Question type is MC, but has no choices.", cell)
                        q_type = _toggle_q_type_and_warn(q_type, q_type_run)
                    state = QuestionFormatterState.ANSWER

            # this is intentionally an if - stem_end should continue onto
            # choices or answer
            if state is QuestionFormatterState.CHOICES and CHOICES_RE.match(para.text):

                try:
                    run_match = _validate_element_text(
                        (choice_run := para.runs[0]), pattern=CHOICES_RE
                    )
                except QuestionParserException as ex:
                    self.log_error(str(ex), cell, level=2)
                    break

                _format_choice(run_match, choice_run, current_choice)

                # save text and update the choice we're looking for
                choices_para[current_choice] = para
                current_choice += 1

                if current_choice == 4:
                    state = QuestionFormatterState.ANSWER

            elif state is QuestionFormatterState.ANSWER and ANSWER_RE.match(para.text):

                para.insert_paragraph_before("")

                if self.force_capitalize:
                    capitalize_paragraph(para)

                if q_type is QuestionType.MULTIPLE_CHOICE:

                    try:
                        test_choice_match = _validate_element_text(para, TEST_CHOICE_RE)
                    except QuestionParserException as ex:
                        self.log_error(str(ex), cell, level=2)
                        break

                    try:
                        _format_answer_line(para, test_choice_match, choices_para)
                    except QuestionParserException as ex:
                        self.log_error(str(ex), cell)

                state = QuestionFormatterState.DONE

        if state is not QuestionFormatterState.DONE:
            self.log_error(f"Parsing failed while looking for {state}", cell, level=2)

        else:
            if self.error_logger is not None:
                self.error_logger.stats[q_type.value] += 1

        return cell


class TuBCellFormatter(CellFormatter):
    def format(self, cell: _Cell) -> _Cell:
        tub_match = TUB_RE.match(cell.text)

        if tub_match:
            put = TossUpBonus.from_string(tub_match.group(1)).value
            clear_cell(cell)
            tub_run = cell.paragraphs[0].runs[0]
            tub_run.text = put
            tub_run.italic = None
            tub_run.bold = None
            highlight_cell_text(cell, None)

            if self.error_logger is not None:
                self.error_logger.stats[put] += 1

        # if a match can't be found, highlight the cell red
        else:
            self.log_error(
                "Question must be a toss-up, bonus, or visual bonus.", cell, level=2
            )

        return cell


class SubjectCellFormatter(CellFormatter):
    def format(self, cell: _Cell) -> _Cell:

        subject_match = SUBJECT_RE.match(cell.text)

        if subject_match:
            put = Subject.from_string(subject_match.group(1)).value
            clear_cell(cell)
            subj_run = cell.paragraphs[0].runs[0]
            subj_run.text = put
            subj_run.italic = None
            subj_run.bold = None
            highlight_cell_text(cell, None)
        # if a match can't be found, highlight the cell red
        else:
            self.log_error("Invalid subject.", cell, level=2)

        return cell


class DifficultyFormatter(CellFormatter):
    def format(self, cell: _Cell) -> _Cell:

        if cell.text:
            try:
                int(cell.text)
            except ValueError:
                self.log_error("LOD should be blank or an integer.", cell, level=2)

        return cell


def _format_question_type_run(q_type_run: Run, run_match: re.Match) -> QuestionType:
    """Returns the type (Multiple Choice or Short Answer) of the question.

    Also handles italicizing the run containing the question type."""
    _q_type = QuestionType.from_string(run_match.group(1))
    # if the run contains more than the question type, split
    # the run into two
    if run_match.span()[1] < len(q_type_run.text):
        q_type_run, _ = split_run_at(q_type_run, run_match.span()[1])

    q_type_run.text, q_type_run.italic = _q_type.value, True
    return _q_type


def _format_answer_line(
    para: Paragraph, test_choice_match: re.Match, choices: Dict[int, Paragraph]
):
    choice_num = CHOICES.index(test_choice_match.group(1) + ")")
    # if answer line is a single letter with an optional ), copy the
    # text of the correct choice over to the answer line
    if test_choice_match.span()[1] <= test_choice_match.span(1)[1] + 1:
        correct_para = choices[choice_num]
        para.text = "ANSWER: "
        for run in correct_para.runs:
            run_copy = deepcopy(run._r)
            run_copy.text = run_copy.text.upper()
            para._p.append(run_copy)
        fuse_consecutive_runs(para)
    # otherwise, check that the answer line text matches the choice.
    # if it doesn't raise a linting error.
    else:
        if (
            choices[choice_num].text.upper()
            != para.text.replace("ANSWER: ", "", 1).upper()
        ):
            highlight_paragraph_text(para, WD_COLOR_INDEX.YELLOW)
            raise QuestionParserException("Answer line doesn't match choice.")


def _validate_element_text(
    run_or_para: Union[Run, Paragraph], pattern: re.Pattern
) -> re.Match:
    """If a recognized part of a question (question type, choices, etc.) is split across
    multiple runs, it won't parse."""

    msgs = {
        TEST_CHOICE_RE: "Found answer line, but couldn't find W, X, Y, or Z.",
        CHOICES_RE: "Couldn't parse question. Check that choices are correct.",
        Q_TYPE_RE: "Couldn't parse question. Check that question type is correct.",
    }

    if not (run_match := pattern.match(run_or_para.text)):
        raise QuestionParserException(msgs[pattern])

    return run_match


def _combine_qtype_and_stem_paragraphs(para: Paragraph) -> None:
    """If a paragraph has only one run, it should be combined with the next paragraph,
    which is presumably the stem paragraph.

    Raises an error of W) or ANSWER: are found in the next paragraph, however."""
    next_para = para._p.getnext()
    next_para_text = "".join(_r.text for _r in next_para if _r.text)
    # need to check if there even IS a stem - next paragraph shouldn't
    # start with W) or ANSWER:
    if CHOICES_RE.match(next_para_text) or ANSWER_RE.match(next_para_text):
        raise QuestionParserException("Couldn't parse question.")

    move_runs_to_end_of_para(next_para, para._p)


def _left_pad_stem(stem_run: Run):
    """All question stems should start with four spaces."""
    stem_run.text = f"    {stem_run.text.lstrip()}"


def _toggle_q_type_and_warn(q_type: QuestionType, q_type_run: Run) -> QuestionType:
    """If a question type is mislabeled, highlight it yellow and toggle the question
    type."""
    q_type_run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    if q_type is QuestionType.SHORT_ANSWER:
        return QuestionType.MULTIPLE_CHOICE
    elif q_type is QuestionType.MULTIPLE_CHOICE:
        return QuestionType.SHORT_ANSWER


def _format_choice(run_match: re.Match, choice_run: Run, current_choice: int):
    """If the wrong choice was matched, replace it with the right choice."""
    if run_match.group(1) != CHOICES[current_choice]:
        choice_run.text = choice_run.text.replace(
            run_match.group(1), CHOICES[current_choice], 1
        )
