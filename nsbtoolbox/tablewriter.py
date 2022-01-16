import re
from copy import deepcopy
from enum import Enum
from functools import lru_cache
from typing import Optional

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.shared import OxmlElement, qn
from docx.shared import Inches, Pt
from docx.table import _Cell, _Row
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from .sciencebowlquestion import QuestionType, Subject, TossUpBonus

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


class QuestionFormatterState(Enum):
    Q_START = 0
    CHOICES = 1
    ANSWER = 2


def insert_run_at_position(par, pos, txt=""):
    """Insert a new run with text {txt} into paragraph {par}
    at given position {pos}.
    Returns the newly created run.
    """
    p = par._p
    new_run = par.add_run(txt)
    p.insert(pos + 1, new_run._r)

    return new_run


def insert_run_before(par, run, txt=""):
    """Insert a new run with text {txt} into paragraph before given {run}.
    Returns the newly created run.
    """
    run_2 = par.add_run(txt)
    run._r.addprevious(run_2._r)

    return run_2


def insert_run_after(par, run, txt=""):
    """Insert a new run with text {txt} into paragraph after given {run}.
    Returns the newly created run.
    """
    run_2 = par.add_run(txt)
    run._r.addnext(run_2._r)

    return run_2


def copy_run_format(run_src, run_dst):
    """Copy formatting from {run_src} to {run_dst}."""
    rPr_target = run_dst._r.get_or_add_rPr()
    rPr_target.addnext(deepcopy(run_src._r.get_or_add_rPr()))
    run_dst._r.remove(rPr_target)


def compare_run_styles(run_1: Run, run_2: Run) -> bool:
    """Nonexhaustively compares two runs to check if they have
    the same font. Science Bowl only uses italic, bold, all caps,
    superscript, subscript, and underline, so only those are
    compared.

    Parameters
    ----------
    run_1, run_2 : Run

    Returns
    -------
    bool
    """
    font_1 = run_1.font
    font_2 = run_2.font

    return (
        (font_1.italic == font_2.italic)
        and (font_1.bold == font_2.bold)
        and (font_1.all_caps == font_2.all_caps)
        and (font_1.superscript == font_2.superscript)
        and (font_1.subscript == font_2.subscript)
        and (font_1.underline == font_1.underline)
    )


def preprocess_cell(cell: _Cell) -> _Cell:
    """Multipass cleaning function for table cells.

    Parameters
    ----------
    cell : _Cell

    Returns
    -------
    _Cell
    """
    for para in cell.paragraphs:

        # this pass combines runs that have the same font properties
        # editing an XML file splits a run, so this is necessary
        # it left-pads the paragraph with empty runs, which will
        # be cleaned up in a later pass.

        for idx, run in enumerate(para.runs[:-1]):
            if compare_run_styles(run, para.runs[idx + 1]):
                para.runs[idx + 1].text = run.text + para.runs[idx + 1].text
                run.text = ""

        # this pass deletes cruft created by the prior pass and coerces
        # the font of any whitespace-only runs to the document style
        for run in para.runs:
            # if there are empty runs, delete them
            if run.text == "":
                delete_run(run)
            # if there are weirdly formatted run that is only whitespace, strip
            # their formatting
            elif run.text.strip() == "":
                run.font.italic = (
                    run.font.bold
                ) = (
                    run.font.all_caps
                ) = (
                    run.font.subscript
                ) = run.font.superscript = run.font.underline = None

        # finally, delete any left padding or right padding for cells containing text
        # delete paragraphs that are empty
        if len(para.runs) == 0:
            delete_paragraph(para)
        else:
            para.runs[0].text = para.runs[0].text.lstrip()
            para.runs[-1].text = para.runs[-1].text.rstrip()

    return cell


def split_run_at(par: Paragraph, run: Run, split_at: int):
    """Splits a run at a specified index.

    Parameters
    ----------
    par : Paragraph
    run : Run
    split_at : int
        Index of split location in the run.

    Returns
    -------
    list of runs
    """
    txt = run.text

    if not isinstance(split_at, int):
        raise ValueError("Split positions must be integer numbers")

    split_at %= len(txt)

    left, right = [txt[:split_at], txt[split_at:]]
    run.text = left
    new_runs = [run]
    new_runs.append(insert_run_after(par, new_runs[0], right))
    copy_run_format(run, new_runs[-1])

    return new_runs


def shade_columns(column, shade: str):
    """Shades a list of cells in-place with a hex color value.

    Parameters
    ----------
    cells : Iterable
        Cells to shade
    shade : str
        Hexadecimal color value
    """
    for cell in column.cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcVAlign = OxmlElement("w:shd")
        tcVAlign.set(qn("w:fill"), shade)
        tcPr.append(tcVAlign)


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


def delete_paragraph(paragraph):
    p = paragraph._element
    p.getparent().remove(p)
    p._p = p._element = None


def delete_run(run):
    p = run._r.getparent()
    p.remove(run._r)


def clear_cell(cell):
    if len(cell.paragraphs) > 1:
        for paragraph in cell.paragraphs[1:]:
            delete_paragraph(paragraph)
    first_para = cell.paragraphs[0]
    if len(first_para.runs) > 1:
        for run in first_para.runs[1:]:
            delete_run(run)
    first_para.runs[0].text = ""


def initialize_table(nrows=0, path: Optional[str] = None) -> Document:
    """Initializes a docx file containing the Science Bowl header row.

    Parameters
    ----------
    nrows : int, optional
        Number of extra rows to append to the table, by default 0

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

    table.cell(0, 0).paragraphs[0].add_run("TUB")
    table.cell(0, 1).paragraphs[0].add_run("Subj")
    ques_run = table.cell(0, 2).paragraphs[0].add_run("Ques")
    ques_run.italic = True
    table.cell(0, 3).paragraphs[0].add_run("LOD")
    table.cell(0, 4).paragraphs[0].add_run("LOD-A")
    table.cell(0, 5).paragraphs[0].add_run("Set")
    table.cell(0, 6).paragraphs[0].add_run("Rd")
    table.cell(0, 7).paragraphs[0].add_run("Q Letter")
    table.cell(0, 8).paragraphs[0].add_run("Author")
    table.cell(0, 9).paragraphs[0].add_run("ID")
    table.cell(0, 10).paragraphs[0].add_run("Source")
    table.cell(0, 11).paragraphs[0].add_run("Comments")
    table.cell(0, 12).paragraphs[0].add_run("Subcat")

    make_jans_shadings(table)

    for idx, column in enumerate(table.columns):
        for cell in column.cells:
            cell.width = Inches(COL_WIDTHS[idx])

    if path is not None:
        document.save(path)

    return document


@lru_cache
def _compile(regex: str):
    return re.compile(regex, re.IGNORECASE)


def format_question_cell(cell: _Cell) -> _Cell:

    # this function performs two passes on each question
    # the first pass removes all whitespace paragraphs
    # and any left or right padding

    for para in cell.paragraphs:
        if para.text.strip() == "":
            delete_paragraph(para)
        else:
            for run in para.runs:
                if run.text.strip() == "":
                    delete_run(run)
            para.runs[0].text = para.runs[0].text.lstrip()
            para.runs[-1].text = para.runs[-1].text.rstrip()

    # the second pass identifies the sections of the questions

    state = QuestionFormatterState.Q_START

    q_type = None

    q_type_possible = _compile(r"\s*(Short Answer|SA|Multiple Choice|MC)\s*")
    choices_re = _compile(r"\s*(W\)|X\)|Y\)|Z\))\s*")
    answer_re = _compile(r"\s*(ANSWER:)\s*")

    choices = ("W)", "X)", "Y)", "Z)")
    current_choice = 0

    for para in cell.paragraphs:

        if state is QuestionFormatterState.Q_START:

            # go through the cell line-by-line and perform an
            # operation based on state
            q_type_match = q_type_possible.match(para.text)
            if q_type_match:
                # the first run of the paragraph should contain the question start
                q_type_run = para.runs[0]
                run_match = q_type_possible.match(q_type_run.text)

                if run_match:
                    q_type = QuestionType.from_string(run_match.group(1))
                    run_length = len(q_type_run.text)
                    # if the run contains more than the question type, split
                    # the run into two
                    if run_match.span()[1] < run_length:
                        q_type_run, _ = split_run_at(
                            para, q_type_run, run_match.span()[1]
                        )

                    q_type_run.text = q_type.value
                    q_type_run.italic = True

                else:
                    # unfortunately, the start of a question might be split up across
                    # several runs if a malicious actor did the formatting. this is
                    # solvable, but I will take care of it later. in the meantime,
                    # the cell will be highlighted red if the question start is not
                    # in a single run.

                    # TODO: if no individual run contains the question start, mix
                    # and match runs until it is found. then, delete all of those runs
                    # except the last, combine all of them, and strip any matching text
                    # out of the next one.
                    highlight_cell_text(cell, WD_COLOR_INDEX.RED)
                    return cell

                # now, the first part of the stem is the second run
                # if it's not left-padded with 4 spaces, make sure it is
                # doing it this way ensures that any other formatting in
                # the stem is preserved (superscripts, subscripts, etc.)
                stem_run = para.runs[1]
                if not stem_run.text.startswith("    "):
                    stem_run.text = "".join(["    ", stem_run.text.lstrip()])

                if q_type is QuestionType.MULTIPLE_CHOICE:
                    state = QuestionFormatterState.CHOICES
                else:
                    state = QuestionFormatterState.ANSWER

        elif state is QuestionFormatterState.CHOICES:

            choice_match = choices_re.match(para.text)
            wrong_answer_match = answer_re.match(para.text)

            # if we match an answer line while looking for choices, maybe
            # the question wasn't actually multiple choice. highlight the
            # question type to indicate this
            if wrong_answer_match:
                q_type_run.font.highlight_color = WD_COLOR_INDEX.RED
                return cell

            if choice_match:
                # insert a blank paragraph before this one. only
                # do this if we are looking for W), the first choice
                if current_choice == 0:
                    para.insert_paragraph_before("")

                # the first run should contain the choice
                choice_run = para.runs[0]
                run_match = choices_re.match(choice_run.text)
                if run_match:
                    # if we matched the wrong choice, replace it with
                    # the right choice
                    if run_match.group(1) != choices[current_choice]:
                        choice_run.text = choice_run.text.replace(
                            run_match.group(1), choices[current_choice], 1
                        )
                    # update the choice we're looking for
                    current_choice += 1
                else:
                    # same problem as above, it is possible that the start of
                    # a choice is spread out over multiple runs.
                    # TODO: fix this problem.
                    highlight_cell_text(cell, WD_COLOR_INDEX.RED)
                    return cell

                # if we just found Z), we're done looking for choices
                if current_choice == 4:
                    current_choice = 0
                    state = QuestionFormatterState.ANSWER

        elif state is QuestionFormatterState.ANSWER:

            # if we find a choice line while looking for an answer,
            # the question is probably not Short Answer. highlight
            # the question type to indicate this
            wrong_choice_match = choices_re.match(para.text)
            if wrong_choice_match:
                q_type_run.font.highlight_color = WD_COLOR_INDEX.YELLOW
                return cell

            answer_match = answer_re.match(para.text)
            if answer_match:
                para.insert_paragraph_before("")

                # set the font to all-caps for every run in the answer line
                for run in para.runs:
                    run.font.all_caps = True

                # TODO: if the question is multiple choice and the answer is only a
                # letter, paste in the rest of the answer. probably requires copying
                # the paragraph that contains the right answer.

                # if we made it here, the cell passed all checks - therefore
                # it should not be highlighted red. instead, highlight it None
                highlight_cell_text(cell, None)
                return cell

    else:
        # if we get through the entire cell without finding all parts of
        # of the question, highlight the cell red
        highlight_cell_text(cell, WD_COLOR_INDEX.RED)
        return cell


def highlight_cell_text(cell: _Cell, color: WD_COLOR_INDEX):
    """Highlights all the text in a cell a given color. Used for
    providing linter warnings.

    Parameters
    ----------
    cell : _Cell
    color : WD_COLOR_INDEX
    """
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.font.highlight_color = color


def format_tub_cell(cell: _Cell) -> _Cell:
    """Formats the TOSS-UP/BONUS cell. Expands shorthand (TU/B/VB) as well.

    Parameters
    ----------
    cell : _Cell

    Returns
    -------
    _Cell
    """
    tub_possible = _compile(r"\s*(TOSS-UP|BONUS|VISUAL BONUS|TU|B|VB)")

    tub_match = tub_possible.match(cell.text)

    if tub_match:
        put = TossUpBonus.from_string(tub_match.group(1)).value
        clear_cell(cell)
        cell.paragraphs[0].add_run(put)
        highlight_cell_text(cell, None)

    # if a match can't be found, highlight the cell red
    else:
        highlight_cell_text(cell, WD_COLOR_INDEX.RED)

    return cell


def format_subject_cell(cell: _Cell) -> _Cell:
    """Formats the Subject cell. Expands shorthand as well.

    Parameters
    ----------
    cell : _Cell

    Returns
    -------
    _Cell
    """
    subject_possible = _compile(
        r"\s*(BIOLOGY|B|CHEMISTRY|C|EARTH AND SPACE|ES|ENERGY|EN|MATH|M|PHYSICS|P)"
    )
    subject_match = subject_possible.match(cell.text)

    if subject_match:
        put = Subject.from_string(subject_match.group(1)).value
        clear_cell(cell)
        cell.paragraphs[0].add_run(put)
        highlight_cell_text(cell, None)
    # if a match can't be found, highlight the cell red
    else:
        highlight_cell_text(cell, WD_COLOR_INDEX.RED)
    return cell


def process_row(nsb_table_row: _Row) -> _Row:

    cells_list = nsb_table_row.cells
    tub_cell = cells_list[0]
    subject_cell = cells_list[1]
    ques_cell = cells_list[2]

    # make sure first cell says TOSS-UP, BONUS, or VISUAL BONUS and nothing else
    format_tub_cell(tub_cell)

    # make sure the second cell says one of our subjects and nothing else
    format_subject_cell(subject_cell)

    # make sure the third cell has a well-formed question
    format_question_cell(ques_cell)

    return nsb_table_row


def format_table(table_doc):
    # first row is the header row, so we skip it
    for row in table_doc.tables[0].rows[1:]:
        process_row(row)
