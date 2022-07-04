from pathlib import Path
from unittest import TestCase

import numpy as np
from numpy.testing import assert_equal

from nsb_toolbox.yamlparsers import (
    ParsedQuestionSpec,
    QuestionDetails,
    SetConfig,
    parse_sets,
)

data_dir = Path(__file__).parent / "test_data"


class TestParsedQuestionSpec(TestCase):
    def setUp(self):
        self.instance = ParsedQuestionSpec.from_yaml_path(
            data_dir / "test_assign_config.yaml"
        )

    def test_simple_config(self):
        config = {
            "Configuration": {"Shuffle Subcategory": False, "Shuffle LOD": False},
            "Round Definitions": {"Tiebreakers": {"TU": {"LOD": [2]}}},
            "Sets": [
                {
                    "Set": ["HSR"],
                    "Prefix": "TB",
                    "Rounds": [1, 2],
                    "Template": "Tiebreakers",
                }
            ],
        }
        expected = [
            QuestionDetails(
                set="HSR",
                round="TB1",
                tub="TU",
                difficulty=2,
                letter="A",
                qtype="SA",
                subcategory=None,
            ),
            QuestionDetails(
                set="HSR",
                round="TB2",
                tub="TU",
                difficulty=2,
                letter="A",
                qtype="SA",
                subcategory=None,
            ),
        ]

        generated = ParsedQuestionSpec.from_yaml_dict(config)
        self.assertEqual(expected, generated.question_list)

    def test_shuffled_config(self):
        config = {
            "Configuration": {
                "Shuffle Subcategory": True,
                "Shuffle LOD": True,
                "Random Seed": 2,
            },
            "Round Definitions": {"Tiebreakers": {"TU": {"LOD": [2, 1, 3]}}},
            "Sets": [
                {
                    "Set": "HSR",
                    "Prefix": "TB",
                    "Rounds": 1,
                    "Template": "Tiebreakers",
                }
            ],
        }

        expected_lod_order = np.array([3, 2, 1])
        generated_lod_order = ParsedQuestionSpec.from_yaml_dict(config).difficulties

        assert_equal(generated_lod_order, expected_lod_order)

    def test_tubs_field(self):
        expected = np.array(
            [
                "TOSS-UP",
                "TOSS-UP",
                "BONUS",
                "BONUS",
                "TOSS-UP",
                "TOSS-UP",
                "BONUS",
                "BONUS",
            ],
            dtype="<U7",
        )
        assert_equal(self.instance.tubs, expected)

    def test_diff_field(self):
        expected = np.array([1, 2, 1, 3, 1, 2, 1, 3])
        assert_equal(self.instance.difficulties, expected)

    def test_qtypes_field(self):
        expected = np.array(["", "Short Answer"] * 4)
        assert_equal(self.instance.qtypes, expected)

    def test_subcat_field(self):
        expected = np.array(["Organic", ""] * 4)
        assert_equal(self.instance.subcategories, expected)

    def test_sets_field(self):
        expected = np.array(["HSR-A"] * 4 + ["HSR-B"] * 4)
        assert_equal(self.instance.sets, expected)

    def test_rounds_field(self):
        expected = np.array(["RR1"] * 8)
        assert_equal(self.instance.rounds, expected)

    def test_qletters_field(self):
        expected = np.array(["A", "B"] * 4)
        assert_equal(self.instance.qletters, expected)


class TestParseSets(TestCase):
    def test_simple_template(self):

        set_config = [
            {"Set": "HSR", "Rounds": 1, "Prefix": "RR", "Template": "RoundRobin"}
        ]
        round_definitions = {"RoundRobin": {"TU": {"LOD": [1, 1, 1, 1]}}}

        generated = parse_sets(set_config, round_definitions)
        expected = [
            SetConfig(
                **{
                    "Set": "HSR",
                    "Prefix": "RR",
                    "Rounds": [1],
                    "Template": {"TU": {"LOD": [1, 1, 1, 1]}},
                }
            )
        ]

        self.assertEqual(generated, expected)

    def test_from_add(self):

        set_config = [
            {
                "Set": "HSR",
                "Prefix": "RR",
                "Rounds": [1, 2],
                "Template": {"from": "RoundRobin", "add": {"TU": {"LOD": [1]}}},
            }
        ]
        round_definitions = {"RoundRobin": {"TU": {"LOD": [1, 1, 1, 1]}}}

        generated = parse_sets(set_config, round_definitions)
        expected = [
            SetConfig(
                **{
                    "Set": "HSR",
                    "Prefix": "RR",
                    "Rounds": [1, 2],
                    "Template": {"TU": {"LOD": [1, 1, 1, 1, 1]}},
                }
            )
        ]

        self.assertEqual(generated, expected)

    def test_malformed(self):

        set_config = [
            {
                "Set": "HSR",
                "Prefix": "RR",
                "Rounds": [1, 2],
                "Template": {"add": {"TU": {"LOD": [1]}}},
            }
        ]
        round_definitions = {"RoundRobin": {"TU": {"LOD": [1, 1, 1, 1]}}}

        with self.assertRaises(KeyError) as ex:
            parse_sets(set_config, round_definitions)
        self.assertIn("If Template is a dictionary, it should", str(ex.exception))
