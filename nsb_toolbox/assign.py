from dataclasses import dataclass, field
from typing import Generator, List

import docx.table
import docx.document

from .yamlparsers import config_to_question_list
from .importers import validate_path, load_doc, load_yaml
from .classes import QuestionType, TossUpBonus


@dataclass
class EditedQuestions:
    document: docx.document.Document

    sets: List[docx.table._Cell] = field(init=False)
    tubs: List[docx.table._Cell] = field(init=False)
    difficulties: List[docx.table._Cell] = field(init=False)
    qtypes: List[docx.table._Cell] = field(init=False)
    subcategories: List[docx.table._Cell] = field(init=False)

    rounds: List[docx.table._Cell] = field(init=False)
    qletters: List[docx.table._Cell] = field(init=False)

    def __post_init__(self):

        cells = self.document.tables[0]._cells
        col_count = self.document.tables[0]._column_count

        # this field can take on any value, so just load it in as a list of strings
        self.subcategories = [
            cells[i].text for i in _col_iter(12, len(cells), col_count)
        ]

        # these fields are all validated, as they can only take on specific values
        try:

            self.tubs = [
                TossUpBonus(cells[i].text) for i in _col_iter(0, len(cells), col_count)
            ]
            self.difficulties = [
                int(cells[i].text) for i in _col_iter(3, len(cells), col_count)
            ]
            self.qtypes = [
                QuestionType(cells[i].paragraphs[0].runs[0].text)
                for i in _col_iter(2, len(cells), col_count)
            ]

        except ValueError as ex:
            raise ValueError(
                "One or more issues with the question document."
                " Have you run nsb format on it?\n",
                ex,
            )

        # these three fields need to be lists of cells because we will modify them later
        self.sets = [cells[i] for i in _col_iter(5, len(cells), col_count)]
        self.rounds = [cells[i] for i in _col_iter(6, len(cells), col_count)]
        self.qletters = [cells[i] for i in _col_iter(7, len(cells), col_count)]

        # rounds and qletters should be empty - if they're not, we'll raise an exception
        if any(x.text for x in self.rounds) or any(x.text for x in self.qletters):
            raise ValueError(
                "The Round and Q Letter columns are not empty in this document."
            )


def _col_iter(
    col_num: int, total_cells: int, col_count: int, skip_header: bool = True
) -> Generator[int, None, None]:
    if skip_header:
        return range(col_num + col_count, total_cells, col_count)
    else:
        return range(col_num, total_cells, col_count)
