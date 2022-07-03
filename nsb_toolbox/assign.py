from dataclasses import dataclass, field
from typing import Generator, List

import docx.table
import docx.document
import numpy as np

from .yamlparsers import config_to_question_list
from .classes import QuestionType, TossUpBonus


@dataclass
class EditedQuestions:
    document: docx.document.Document

    tubs: List[TossUpBonus] = field(init=False)
    difficulties: List[int] = field(init=False)
    qtypes: List[QuestionType] = field(init=False)
    subcategories: List[str] = field(init=False)

    sets: List[docx.table._Cell] = field(init=False)
    rounds: List[docx.table._Cell] = field(init=False)
    qletters: List[docx.table._Cell] = field(init=False)

    def __post_init__(self):

        cells = self.document.tables[0]._cells
        col_count = self.document.tables[0]._column_count

        # this field can take on any value, so just load it in as a list of strings
        self.subcategories = np.array(
            [cells[i].text for i in _col_iter(12, len(cells), col_count)], dtype="<U20"
        )

        # these fields are all validated, as they can only take on specific values
        try:

            self.tubs = np.array(
                [
                    TossUpBonus(cells[i].text).value
                    for i in _col_iter(0, len(cells), col_count)
                ],
                dtype="<U20",
            )
            self.difficulties = np.array(
                [int(cells[i].text) for i in _col_iter(3, len(cells), col_count)]
            )
            self.qtypes = np.array(
                [
                    QuestionType(cells[i].paragraphs[0].runs[0].text).value
                    for i in _col_iter(2, len(cells), col_count)
                ],
                dtype="<U20",
            )

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


@dataclass
class ParsedQuestionSpec:
    config_yaml: dict

    tubs: List[TossUpBonus] = field(init=False)
    difficulties: List[int] = field(init=False)
    qtypes: List[QuestionType] = field(init=False)
    subcategories: List[str] = field(init=False)

    sets: List[str] = field(init=False)
    rounds: List[str] = field(init=False)
    qletters: List[str] = field(init=False)

    def __post_init__(self):
        q_list = config_to_question_list(self.config_yaml)

        self.tubs = np.empty(len(q_list), dtype="<U20")
        self.difficulties = np.empty(len(q_list), dtype=int)
        self.qtypes = np.empty(len(q_list), dtype="<U20")
        self.subcategories = np.empty(len(q_list), dtype="<U20")

        self.sets = np.empty(len(q_list), dtype="<U20")
        self.rounds = np.empty(len(q_list), dtype="<U20")
        self.qletters = np.empty(len(q_list), dtype="<U20")

        for idx, question in enumerate(q_list):

            self.tubs[idx] = question.tub.value
            self.difficulties[idx] = question.difficulty
            self.qtypes[idx] = question.qtype.value if question.qtype else ""
            self.subcategories[idx] = (
                question.subcategory if question.subcategory else ""
            )

            self.sets[idx] = question.set
            self.rounds[idx] = question.round
            self.qletters[idx] = question.letter


def _col_iter(
    col_num: int, total_cells: int, col_count: int, skip_header: bool = True
) -> Generator[int, None, None]:
    if skip_header:
        return range(col_num + col_count, total_cells, col_count)
    else:
        return range(col_num, total_cells, col_count)
