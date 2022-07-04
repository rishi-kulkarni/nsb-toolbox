from pathlib import Path

import numpy as np
import pytest
from nsb_toolbox.assign import EditedQuestions
from nsb_toolbox.importers import load_doc
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
