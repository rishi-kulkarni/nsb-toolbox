import re
from pathlib import Path

import numpy as np
import pytest
from nsb_toolbox.assign import EditedQuestions
from nsb_toolbox.importers import load_doc
from nsb_toolbox.tables import COL_MAPPING
from nsb_toolbox.yamlparsers import ParsedQuestionSpec

data_dir = Path(__file__).parent / "test_data"


@pytest.fixture
def doc_path():
    return data_dir / "test_assign_questions.docx"


@pytest.fixture(params=["doc", "path"])
def instance(doc_path, request):
    if request.param == "doc":
        doc = load_doc(doc_path)
        return EditedQuestions(doc)
    elif request.param == "path":
        return EditedQuestions.from_docx_path(doc_path)


class TestEditedQuestionsFields:
    def test_tub_field(self, instance):
        for tub in instance.tubs:
            assert tub in ("TOSS-UP", "BONUS")

    def test_set_field(self, instance):
        for set_ in instance.sets:
            assert hasattr(set_, "text")

    def test_diff_field(self, instance):
        for lod in instance.difficulties:
            assert np.issubdtype(lod, np.integer)

    def test_qtypes_field(self, instance):
        for qtype in instance.qtypes:
            assert qtype in ("Multiple Choice", "Short Answer")

    def test_subcat_field(self, instance):

        for subcat in instance.subcategories:
            assert isinstance(subcat, str)

    def test_rounds_field(self, instance):

        for round_ in instance.rounds:
            assert hasattr(round_, "text")

    def test_qletter_field(self, instance):

        for qletter in instance.qletters:
            assert hasattr(qletter, "text")

    def test_writer_field(self, instance):

        for writer in instance.writers:
            assert isinstance(writer, str)

    @pytest.mark.parametrize("col_index", [0, 2, 3])
    def test_invalid_tubs(self, doc_path, col_index):

        doc = load_doc(doc_path)
        doc.tables[0].column_cells(col_index)[1].text = "Invalid"

        with pytest.raises(
            ValueError, match="One or more issues with the question document"
        ):
            EditedQuestions(doc)


@pytest.fixture(params=["raw", "prefer_writers"])
def question_spec(request):
    spec = ParsedQuestionSpec.from_yaml_path(data_dir / "test_assign_config.yaml")
    if request.param == "raw":
        spec.config.shuffle_difficulty = False
        spec.config.preferred_writers = []
        spec.config.shuffle_pairs = False
        spec.config.shuffle_subcategory = False
        spec.config.subcat_mismatch_penalty = 1
        spec.config.rng = np.random.default_rng()
        return spec
    if request.param == "prefer_writers":
        spec.config.shuffle_difficulty = False
        spec.config.preferred_writers = ["Chen, Andrew", "Kulkarni, Rishi"]
        spec.config.shuffle_pairs = False
        spec.config.shuffle_subcategory = False
        spec.config.subcat_mismatch_penalty = 1
        spec.config.rng = np.random.default_rng()
        return spec


class TestEditedQuestionsAssign:
    """Tests the EditedQuestions.assign method."""

    def test_assign_contract_is_met(self, question_spec, doc_path):
        questions = EditedQuestions.from_docx_path(doc_path)
        pre_assign_sets = [x.text for x in questions.sets]

        questions.assign(question_spec)

        post_assign_sets = [x.text for x in questions.sets]

        # check that pre-specified sets are respected
        for pre, post in zip(pre_assign_sets, post_assign_sets):
            assert pre == post or pre == "HSR"

        assignments = [
            f"{tub}-{set_.text}-{rd.text}-{let.text}"
            for tub, set_, rd, let in zip(
                questions.tubs, questions.sets, questions.rounds, questions.qletters
            )
            if rd.text
        ]

        # check that each assignment is unique
        assert len(assignments) == len(np.unique(assignments))

        # check that each question in the spec was assigned
        assert len(assignments) == len(question_spec.question_list)

    def test_sort_assignments_orders_rows(self, question_spec, doc_path):

        questions = EditedQuestions.from_docx_path(doc_path)
        questions.assign(question_spec)
        questions.sort_assignments(question_spec)

        table = questions.document.tables[0]
        data_rows = list(table.rows)[1:]

        assigned_rows = [
            row for row in data_rows if row.cells[COL_MAPPING["Rd"]].text.strip()
        ]

        expected_count = len(question_spec.question_list)
        assert len(assigned_rows) >= expected_count

        observed = [
            (
                row.cells[COL_MAPPING["Set"]].text.strip(),
                row.cells[COL_MAPPING["Rd"]].text.strip(),
                row.cells[COL_MAPPING["Q Letter"]].text.strip().upper(),
                row.cells[COL_MAPPING["TUB"]].text.strip(),
            )
            for row in assigned_rows[:expected_count]
        ]

        set_order = {}
        prefix_order = {}
        round_priority = {}
        letter_order = {}

        round_pattern = re.compile(r"^([^\d]*)(\d+)(.*)$")

        def decompose_round(value: str):
            match = round_pattern.match(value)
            if match:
                prefix, number, suffix = match.groups()
                return prefix, int(number), suffix
            return value, float("inf"), ""

        for detail in question_spec.question_list:
            set_order.setdefault(detail.set, len(set_order))

            prefix, number, suffix = decompose_round(detail.round)
            prefix_map = prefix_order.setdefault(detail.set, {})
            prefix_idx = prefix_map.setdefault(prefix, len(prefix_map))

            round_map = round_priority.setdefault(detail.set, {})
            round_map.setdefault(
                detail.round,
                (prefix_idx, number, suffix, len(round_map)),
            )

            letter_order.setdefault(detail.letter.upper(), len(letter_order))

        def round_key(detail):
            round_map = round_priority.get(detail.set, {})
            if detail.round in round_map:
                return round_map[detail.round]
            prefix, number, suffix = decompose_round(detail.round)
            prefix_idx = prefix_order.get(detail.set, {}).get(
                prefix,
                len(prefix_order.get(detail.set, {})),
            )
            return (prefix_idx, number, suffix, len(round_map))

        tub_priority = {"TOSS-UP": 0, "BONUS": 1, "VISUAL BONUS": 2}

        expected_details = sorted(
            question_spec.question_list,
            key=lambda detail: (
                set_order[detail.set],
                round_key(detail),
                letter_order[detail.letter.upper()],
                tub_priority[detail.tub.value],
            ),
        )

        expected = [
            (detail.set, detail.round, detail.letter, detail.tub.value)
            for detail in expected_details
        ]

        assert observed == expected

    def test_user_checkin_before_reassign(self, question_spec, doc_path, monkeypatch):

        monkeypatch.setattr("builtins.input", lambda _: "n")

        questions = EditedQuestions.from_docx_path(doc_path)

        with pytest.raises(ValueError, match="Aborted!"):
            questions.assign(question_spec)
            questions.assign(question_spec)

    def test_reassign_contract_is_met(self, question_spec, doc_path, monkeypatch):

        monkeypatch.setattr("builtins.input", lambda _: "y")

        questions = EditedQuestions.from_docx_path(doc_path)

        pre_assign_sets = [x.text for x in questions.sets]

        questions.assign(question_spec)
        questions.assign(question_spec)
        questions.assign(question_spec)
        questions.assign(question_spec)
        questions.assign(question_spec)
        questions.assign(question_spec)
        questions.assign(question_spec)
        questions.assign(question_spec)
        questions.assign(question_spec)

        post_assign_sets = [x.text for x in questions.sets]

        # check that pre-specified sets are respected
        for pre, post in zip(pre_assign_sets, post_assign_sets):
            assert pre == post or pre == "HSR"

        assignments = [
            f"{tub}-{set_.text}-{rd.text}-{let.text}"
            for tub, set_, rd, let in zip(
                questions.tubs, questions.sets, questions.rounds, questions.qletters
            )
            if rd.text
        ]

        # check that each assignment is unique
        assert len(assignments) == len(np.unique(assignments))

        # check that each question in the spec was assigned
        assert len(assignments) == len(question_spec.question_list)

    def test_exception_when_assignment_failure(self, doc_path):
        questions = EditedQuestions.from_docx_path(doc_path)

        config_dict = {
            "Configuration": {
                "Shuffle Subcategory": False,
                "Shuffle Pairs": False,
                "Shuffle LOD": False,
                "Random Seed": None,
                "Subcategory Mismatch Penalty": 1,
                "Preferred Writers": ["Chen, Andrew", "Kulkarni, Rishi"],
            },
            "Round Definitions": {
                "RoundRobin": {
                    "TU": {"LOD": [1, 2, 3, 4], "Subcategory": ["Organic", None]},
                }
            },
            "Sets": [
                {
                    "Set": ["HSR-A", "HSR-B"],
                    "Prefix": "RR",
                    "Rounds": [1],
                    "Template": "RoundRobin",
                }
            ],
        }

        question_spec = ParsedQuestionSpec.from_yaml_dict(config_dict)

        with pytest.raises(
            ValueError, match="Failed to assign. Do you have enough questions?"
        ):
            questions.assign(question_spec)

    def test_exception_when_fewer_questions_than_spec_requires(self, doc_path):
        questions = EditedQuestions.from_docx_path(doc_path)

        config_dict = {
            "Configuration": {
                "Shuffle Subcategory": False,
                "Shuffle Pairs": False,
                "Shuffle LOD": False,
                "Random Seed": None,
                "Subcategory Mismatch Penalty": 1,
                "Preferred Writers": ["Chen, Andrew", "Kulkarni, Rishi"],
            },
            "Round Definitions": {
                "RoundRobin": {
                    "TU": {
                        "LOD": [1, 2, 3, 4, 5, 6, 7, 8],
                        "Subcategory": ["Organic", None],
                    },
                    "B": {
                        "LOD": [1, 2, 3, 4, 5, 6, 7, 8],
                        "Subcategory": ["Organic", None],
                    },
                }
            },
            "Sets": [
                {
                    "Set": ["HSR-A", "HSR-B"],
                    "Prefix": "RR",
                    "Rounds": [1],
                    "Template": "RoundRobin",
                }
            ],
        }

        question_spec = ParsedQuestionSpec.from_yaml_dict(config_dict)

        with pytest.raises(
            ValueError, match="There are not enough available questions"
        ):
            questions.assign(question_spec)
