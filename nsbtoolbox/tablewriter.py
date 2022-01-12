from typing import Iterable
from docx import Document
from docx.shared import Inches
from docx.oxml.shared import OxmlElement, qn

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
