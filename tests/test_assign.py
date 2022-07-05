from pathlib import Path

import numpy as np
import pytest
from nsb_toolbox.assign import EditedQuestions
from nsb_toolbox.importers import load_doc
from nsb_toolbox.yamlparsers import ParsedQuestionSpec
from numpy.testing import assert_equal

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
        expected_tub = np.array(["TOSS-UP"] * 6 + ["BONUS"] * 6)
        assert_equal(instance.tubs, expected_tub)

    def test_set_field(self, instance):
        expected_sets = ["HSR-A", "HSR-B", "HSR", "HSR", "HSR", "HSR"] * 2
        assert [x.text for x in instance.sets] == expected_sets

    def test_diff_field(self, instance):
        expected_difficulties = np.array([1, 2, 3, -1, 3, 3, 1, 2, 3, 4, 2, -1])
        assert_equal(instance.difficulties, expected_difficulties)

    def test_qtypes_field(self, instance):
        expected_qtypes = np.array(
            ["Multiple Choice"] * 3
            + ["Short Answer"] * 7
            + ["Multiple Choice"]
            + ["Short Answer"]
        )
        assert_equal(instance.qtypes, expected_qtypes)

    def test_subcat_field(self, instance):

        expected_subcategories = np.array([""] * 4 + ["Organic"] * 4 + [""] * 4)
        assert_equal(instance.subcategories, expected_subcategories)

    def test_rounds_field(self, instance):

        expected_rounds = [""] * 12
        assert [x.text for x in instance.rounds] == expected_rounds

    def test_qletter_field(self, instance):

        expected_qletters = [""] * 12
        assert [x.text for x in instance.qletters] == expected_qletters

    def test_writer_field(self, instance):

        expected_writers = np.array(
            [""] * 7
            + [
                "Walfred",
                "Chen, Andrew",
                "",
                "Kulkarni, Rishi",
                "",
            ]
        )

        assert_equal(instance.writers, expected_writers)

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
        spec.config.rng = np.random.default_rng(1)
        return spec
    if request.param == "prefer_writers":
        spec.config.shuffle_difficulty = False
        spec.config.preferred_writers = ["Chen, Andrew", "Kulkarni, Rishi"]
        spec.config.shuffle_pairs = False
        spec.config.shuffle_subcategory = False
        spec.config.subcat_mismatch_penalty = 1
        spec.config.rng = np.random.default_rng(1)
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

    def test_user_checkin_before_reassign(self, question_spec, doc_path, monkeypatch):

        monkeypatch.setattr("builtins.input", lambda _: "n")

        questions = EditedQuestions.from_docx_path(doc_path)

        with pytest.raises(ValueError, match="Aborted!"):
            questions.assign(question_spec)
            questions.assign(question_spec)

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
            ValueError, match="Failed to assign the following questions:"
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
