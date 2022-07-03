from unittest import TestCase

from nsb_toolbox.yamlparsers import (
    QuestionDetails,
    SetConfig,
    parse_sets,
    config_to_question_list,
)


class TestConfigtoQuestionList(TestCase):
    def setUp(self):
        self.config = {
            "Shuffle": {"Subcategory": False, "LOD": False},
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

    def test_simple_config(self):
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

        generated = config_to_question_list(self.config)
        self.assertEqual(expected, generated)

    def test_shuffled_config(self):
        config = {
            "Shuffle": {"Subcategory": True, "LOD": True, "Seed": 2},
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

        expected_lod_order = [3, 2, 1]
        generated_lod_order = [x.difficulty for x in config_to_question_list(config)]

        self.assertEqual(generated_lod_order, expected_lod_order)


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
