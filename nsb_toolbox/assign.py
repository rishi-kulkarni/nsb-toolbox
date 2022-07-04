from functools import cached_property
from pathlib import Path
from typing import Generator, List, Optional, Union
from typing_extensions import Self

import docx.table
import docx.document
import numpy as np
from scipy.optimize import linear_sum_assignment

from nsb_toolbox.importers import load_doc

from .classes import QuestionType, TossUpBonus
from .yamlparsers import ParsedQuestionSpec


class EditedQuestions:
    """Represents an edited set of Science Bowl questions from a single subject
    with level of difficulty and subcategory assigned by the SME.

    Parameters
    ----------
    document : docx.document.Document
        Word document of Science Bowl questions wrapped by this class.

    Raises
    ------
    ValueError
        Raised if there are formatting issues in the document.

    Attributes
    ----------
    tubs : np.ndarray[str]
    difficulties : np.ndarray[int]
    qtypes : np.ndarray[str]
    subcategories : np.ndarray[str]
    sets : List[docx.table._Cell]
    rounds : List[docx.table._Cell]
    qletters : List[docx.table._Cell]

    Methods
    -------
    assign(question_spec: ParsedQuestionSpec)
        Assigns the questions to a specification via a linear sum assignment.
    """

    def __init__(self, document: docx.document.Document) -> Self:

        self.document = document

        self._cells = self.document.tables[0]._cells
        self._col_count = self.document.tables[0]._column_count

        try:
            self.difficulties
            self.tubs
            self.qtypes
        except ValueError as ex:
            raise ValueError(
                "One or more issues with the question document."
                " Have you run nsb format on it?\n",
                ex,
            )

    @classmethod
    def from_docx_path(cls, path: Union[Path, str]) -> Self:
        doc = load_doc(path)
        return cls(doc)

    @cached_property
    def tubs(self) -> np.ndarray:
        return np.array(
            [
                TossUpBonus(self._cells[i].text).value
                for i in _col_iter(0, len(self._cells), self._col_count)
            ],
            dtype="<U20",
        )

    @cached_property
    def difficulties(self) -> np.ndarray:
        return np.array(
            [
                int(self._cells[i].text)
                for i in _col_iter(3, len(self._cells), self._col_count)
            ]
        )

    @cached_property
    def qtypes(self) -> np.ndarray:
        return np.array(
            [
                QuestionType(self._cells[i].paragraphs[0].runs[0].text).value
                for i in _col_iter(2, len(self._cells), self._col_count)
            ],
            dtype="<U20",
        )

    @cached_property
    def subcategories(self) -> np.ndarray:
        return np.array(
            [
                self._cells[i].text
                for i in _col_iter(12, len(self._cells), self._col_count)
            ],
            dtype="<U20",
        )

    @property
    def sets(self) -> List[docx.table._Cell]:
        return [self._cells[i] for i in _col_iter(5, len(self._cells), self._col_count)]

    @property
    def rounds(self) -> List[docx.table._Cell]:
        return [self._cells[i] for i in _col_iter(6, len(self._cells), self._col_count)]

    @property
    def qletters(self) -> List[docx.table._Cell]:
        return [self._cells[i] for i in _col_iter(7, len(self._cells), self._col_count)]

    def assign(self, question_spec: ParsedQuestionSpec):
        """Attempts to find a valid assignment of the questions to question_spec via a
        linear sum assignment. Upon success, writes the successful assignment to the
        question document. Otherwise, notifies the user which parts of the specification
        could not be met.

        Parameters
        ----------
        question_spec : ParsedQuestionSpec
            Question specification read from a config file.

        Raises
        ------
        ValueError
            Raised if the questions cannot meet the given specification. Prints
            the specifications that cannot be met so that the SME can find appropriate
            questions.
        """
        self._validate()

        cost_matrix = build_cost_matrix(
            questions=self, spec=question_spec, rng=question_spec.config.rng
        )

        q_assignments, round_assignments = linear_sum_assignment(cost_matrix)
        assignment_costs = cost_matrix[q_assignments, round_assignments]

        if assignment_costs.sum() > 1_000_000:
            self._raise_assignment_failure(question_spec, assignment_costs)

        else:
            print("Found a successful set of assignments!")
            self._write_assignment(question_spec, q_assignments, round_assignments)

    def _write_assignment(
        self,
        question_spec: ParsedQuestionSpec,
        q_assignments: np.ndarray,
        round_assignments: np.ndarray,
    ):
        """In case of assignment success, write successful assignemnt to
        this question set."""
        for q_idx, spec_idx in zip(q_assignments, round_assignments):
            self.sets[q_idx].text = question_spec.sets[spec_idx]
            self.rounds[q_idx].text = question_spec.rounds[spec_idx]
            self.qletters[q_idx].text = question_spec.qletters[spec_idx]

    def _raise_assignment_failure(
        self, question_spec: ParsedQuestionSpec, assignment_costs: np.ndarray
    ):
        """In case assignment fails, find the questions in the spec that failed to
        be assigned and return them to the user."""
        where_bad_assigns = np.argwhere(
            assignment_costs == assignment_costs.max()
        ).ravel()
        failed_assignments = [
            str(question_spec.question_list[idx]) for idx in where_bad_assigns
        ]

        _NL = "\n"
        raise ValueError(
            "Failed to assigned the following "
            f"questions:\n{_NL.join(failed_assignments)}"
        )

    def _validate(self):
        """Rounds and question letters in self.document should be empty. If not,
        ask the user to confirm that they intend to overwrite them."""
        if any(x.text for x in self.rounds) or any(x.text for x in self.qletters):
            while True:
                user_input = input(
                    "The Round and Q Letter columns are not empty in this document.\n"
                    "Continuing will overwrite the current assignments. Continue? (Y/n)"
                )
                if user_input.lower() in ("y", "n"):
                    break

            if user_input.lower == "n":
                raise ValueError("Aborted!")


def build_cost_matrix(
    questions: EditedQuestions,
    spec: ParsedQuestionSpec,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """Computes a cost matrix for assigning a set of Science Bowl questions to a
    given question specification.

    Parameters
    ----------
    questions : EditedQuestions
    spec : ParsedQuestionSpec

    Returns
    -------
    np.ndarray
        Cost matrix with questions represented by rows and slots by columns.
    """
    # randomness, can be seeded in the config file
    if rng is None:
        rng = np.random.default_rng()

    random_matrix = rng.uniform(
        0,
        0.0001,
        size=(questions.difficulties.size, spec.difficulties.size),
    )

    # squared loss for difficulties
    diff_matrix = (spec.difficulties - questions.difficulties[:, None]) ** 2

    # penalize subcategory mismatches
    # TODO: this penalty should be parameterized in the config
    subcat_matrix = np.where(
        (spec.subcategories != questions.subcategories[:, None])
        & (spec.subcategories != ""),
        1,
        0,
    )

    cost_matrix = random_matrix + diff_matrix + subcat_matrix

    # mask to indicate where toss-up/bonus do not match
    tub_mask = spec.tubs != questions.tubs[:, None]
    # mask to indicate where Short Answer/Multiple Choice do not match
    qtype_mask = (spec.qtypes != questions.qtypes[:, None]) & (spec.qtypes != "")
    # mask to indicate where Sets are compatible
    q_sets = np.array([x.text for x in questions.sets])[:, None]
    # each doc should represent one packet, so this throws an error if we get more
    # than one.
    (packet,) = np.unique([x.split("-")[0] for x in spec.sets])
    set_mask = (spec.sets != q_sets) & (q_sets != packet)

    # anywhere
    mask = tub_mask | qtype_mask | set_mask
    cost_matrix[mask] = 1_000_000

    return cost_matrix


def _col_iter(
    col_num: int, total_cells: int, col_count: int, skip_header: bool = True
) -> Generator[int, None, None]:
    if skip_header:
        return range(col_num + col_count, total_cells, col_count)
    else:
        return range(col_num, total_cells, col_count)
