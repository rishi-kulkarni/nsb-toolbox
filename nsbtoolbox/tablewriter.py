import docx
from typing import Iterable
from docx import Document
from docx.shared import Inches
from docx.oxml.shared import OxmlElement, qn
from docx.enum.text import WD_COLOR_INDEX
from docx.table import _Cell
from functools import lru_cache
import re
from .sciencebowlquestion import TossUpBonus, Subject, QuestionType
from copy import deepcopy

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


def split_run_at(par: docx.text.paragraph.Paragraph, run_idx: int, split_at: int):
    """Splits a run at a specified index.

    Parameters
    ----------
    par : docx.text.paragraph.Paragraph
    run_idx : int
        Index of run to be split.
    split_at : int
        Index of split location in the run.

    Returns
    -------
    list of runs
    """
    run = par.runs[run_idx]
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


def shade_cells(cells: Iterable, shade: str):
    """Shades a list of cells in-place with a hex color value.

    Parameters
    ----------
    cells : Iterable
        Cells to shade
    shade : str
        Hexadecimal color value
    """
    for cell in cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcVAlign = OxmlElement("w:shd")
        tcVAlign.set(qn("w:fill"), shade)
        tcPr.append(tcVAlign)


def make_jans_shadings(row):
    """Shades the 4, 6, 7, and 8th cells in a row the appropriate colors.

    Parameters
    ----------
    row : Document.rows object
    """
    shade_cells([row.cells[3]], "#FFCC99")
    shade_cells([row.cells[5]], "#e5dfec")
    shade_cells([row.cells[6], row.cells[7]], "#daeef3")


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


def initialize_table(path: str) -> Document:
    """Initializes a docx file containing the Science Bowl header row.

    Parameters
    ----------
    path : str
        Path that the docx file should be saved to.

    Returns
    -------
    Document
    """
    document = Document()
    table = document.add_table(rows=1, cols=13)

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

    for idx, inches in enumerate(COL_WIDTHS):
        col = table.columns[idx].cells[0]
        col.width = Inches(inches)

    make_jans_shadings(table.rows[0])

    document.save(path)

    return document


@lru_cache
def _compile(regex: str):
    return re.compile(regex, re.IGNORECASE)


def process_question_cell(cell: _Cell):
    q_type = None
    q_type_possible = _compile(r"\s*(Short Answer|SA|Multiple Choice|MC)\s*")

    for idx, para in enumerate(cell.paragraphs):
        # go through the cell line-by-line until we find the start of a question
        q_type_match = q_type_possible.match(para.text)
        if q_type_match:
            q_start_line = idx
            # delete any paragraphs above the start of the question
            for to_delete in cell.paragraphs[:q_start_line]:
                delete_paragraph(to_delete)

            # go through the line run-by-run until we find the start of the question
            # there can be infinite empty runs anywhere in a document
            for run_idx, run in enumerate(para.runs):
                run_match = q_type_possible.match(run.text)

                if run_match:
                    q_type = QuestionType.from_string(run_match.group(1))
                    for to_delete in para.runs[:run_idx]:
                        delete_run(to_delete)
                    run_length = len(run.text)
                    # if the run contains more than the question type, split
                    # the run into two
                    if run_match.span()[1] < run_length:
                        run, _ = split_run_at(para, run_idx, run_match.span()[1])

                    run.text = q_type.value
                    run.italic = True

                    break

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
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.highlight_color = WD_COLOR_INDEX.RED

            # now, the first part of the stem is the second run
            # if it's not left-padded with 4 spaces, make sure it is
            # doing it this way ensures that any other formatting in
            # the stem is preserved (superscripts, subscripts, etc.)
            stem_run = para.runs[1]
            if not stem_run.text.startswith("    "):
                stem_run.text = "".join(["    ", stem_run.text.lstrip()])

            # need to know the last index the stem is on so we can make
            # sure there is a blank line between the question and the answer
            # since we may have deleted paragraphs, have to look up the
            # index again
            stem_idx = [x.text for x in cell.paragraphs].index(para.text)
            break
    else:
        # if the start of the question is not found, indicate an error
        # by highlighting the cell red
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.highlight_color = WD_COLOR_INDEX.RED

    # if the question is multiple choice, the next line of interest
    # will start with W), X), Y), or Z). all options will be considered
    # because people frequently make typos.
    if q_type is QuestionType.MULTIPLE_CHOICE:
        choices = ("W)", "X)", "Y)", "Z)")
        choices_re = _compile(r"\s*(W\)|X\)|Y\)|Z\))\s*")
        current_choice = 0

        for idx, para in enumerate(cell.paragraphs[stem_idx:]):
            print(idx)
            choice_match = choices_re.match(para.text)

            # if the next paragraph after the stem doesn't start with
            # W)-Z), it's likely that there's a paragraph break in the
            # middle of the stem. thus ignore the paragraph and update
            # the index representing the end of the stem
            if para.text.strip() != "" and not choice_match and current_choice == 0:
                stem_idx += 1
                continue

            elif para.text.strip() == "" and current_choice > 0:
                delete_paragraph(para)

            elif choice_match:
                choice_start_idx = idx
                # delete paragraphs between end of stem and start of first
                # choice, then insert a blank paragraph. only do this if
                # we are looking for W), the first choice
                if current_choice == 0:
                    for to_delete in cell.paragraphs[stem_idx:choice_start_idx]:
                        delete_paragraph(to_delete)
                    para.insert_paragraph_before("")

                # next, find the run that contains the start of the choice
                for run_idx, run in enumerate(para.runs):
                    run_match = choices_re.match(run.text)
                    if run_match:
                        # delete any prior runs
                        for to_delete in para.runs[:run_idx]:
                            delete_run(to_delete)
                        # if we matched the wrong choice, replace it with
                        # the right choice
                        if run_match.group(1) != choices[current_choice]:
                            run.text = run.text.replace(
                                run_match.group(1), choices[current_choice], 1
                            )
                        # update the choice we're looking for
                        current_choice += 1
                        break
                else:
                    # same problem as above, it is possible that the start of
                    # a choice is spread out over multiple runs.
                    # TODO: fix this problem.
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.highlight_color = WD_COLOR_INDEX.RED

                # if we just found Z), we're done looking for choices
                if current_choice == 4:
                    print("Found all choices")
                    current_choice = 0
                    choices_end_idx = [x.text for x in cell.paragraphs].index(para.text)
                    break

            else:
                continue

        # if we failed to find 4 choices before hitting the end
        # of the cell, highlight the cell to indicate a problem
        else:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.highlight_color = WD_COLOR_INDEX.RED


def process_row(nsb_table_row):

    cells_list = nsb_table_row.cells

    # make sure first cell says TOSS-UP, BONUS, or VISUAL BONUS and nothing else
    # writers can put TU, B, or VB as shorthand and this will expand it

    tub_possible = _compile(r"\s*(TOSS-UP|BONUS|VISUAL BONUS|TU|B|VB)")
    tub_cell = cells_list[0]

    tub_match = tub_possible.match(tub_cell.text)

    if tub_match:
        put = TossUpBonus.from_string(tub_match.group(1)).value
        clear_cell(tub_cell)
        tub_cell.paragraphs[0].add_run(put)

    else:
        for paragraph in tub_cell.paragraphs:
            for run in paragraph.runs:
                run.font.highlight_color = WD_COLOR_INDEX.RED

    # make sure the second cell says one of our subjects and nothing else
    # shorthand is, once again, allowed

    subject_possible = _compile(
        r"\s*(BIOLOGY|B|CHEMISTRY|C|EARTH AND SPACE|ES|ENERGY|EN|MATH|M|PHYSICS|P)"
    )
    subject_cell = cells_list[1]

    subject_match = subject_possible.match(subject_cell.text)

    if subject_match:
        put = Subject.from_string(subject_match.group(1)).value
        clear_cell(subject_cell)
        subject_cell.paragraphs[0].add_run(put)
    else:
        for paragraph in subject_cell.paragraphs:
            for run in paragraph.runs:
                run.font.highlight_color = WD_COLOR_INDEX.RED


def format_table(table_doc):
    # first row is the header row, so we skip it
    for row in table_doc.tables[0].rows[1:]:
        process_row(row)
