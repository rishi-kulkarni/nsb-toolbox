import collections.abc
import itertools
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, Generator, List, Optional

import numpy as np

from .classes import QuestionType, TossUpBonus


@dataclass
class QuestionDetails:
    set: str
    round: str
    tub: TossUpBonus
    difficulty: int
    letter: str
    qtype: Optional[QuestionType] = None
    subcategory: Optional[str] = None

    def __post_init__(self):

        if isinstance(self.tub, str):
            self.tub = TossUpBonus.from_string(self.tub)

        if isinstance(self.qtype, str):
            self.qtype = QuestionType.from_string(self.qtype)


@dataclass
class ShuffleConfig:
    subcategory: bool
    difficulty: bool
    rng: np.random.Generator

    def __post_init__(self):
        if not isinstance(self.rng, np.random.Generator):
            self.rng = np.random.default_rng(self.rng)


@dataclass
class SetConfig:
    Set: List[str]
    Prefix: str
    Rounds: List[int]
    Template: dict

    def __post_init__(self):
        if isinstance(self.Set, str):
            self.Set = [self.Set]

        if isinstance(self.Rounds, int):
            self.Rounds = [self.Rounds]


def config_to_question_list(config: Dict) -> List[QuestionDetails]:
    """Converts a configuration dictionary into a list of QuestionDetails
    specifications.

    Parameters
    ----------
    config : Dict
        Dictionary loaded from a yaml config using `load_yaml`.

    Returns
    -------
    List[QuestionDetails]
        Complete question specification for the config file.
    """
    shuffle_config = _parse_shuffle(config["Shuffle"])
    round_definitions = config["Round Definitions"]

    parsed_sets = parse_sets(config["Sets"], round_definitions)

    return list(
        generate_questions(parsed_sets=parsed_sets, shuffle_config=shuffle_config)
    )


def generate_questions(
    parsed_sets: Dict, shuffle_config: ShuffleConfig
) -> Generator[QuestionDetails, None, None]:
    """Generates QuestionDetails instances based on a parsed set of
    Science Bowl round descriptions and a ShuffleConfig instance.

    Parameters
    ----------
    parsed_sets : Dict
        Science Bowl set specification generated with parse_sets.
    shuffle_config : ShuffleConfig
        Determines if subcategories and difficulties are shuffled
        within each round.

    Yields
    ------
    Generator[QuestionDetails, None, None]

    Notes
    -----

    The convention that the last pair of questions for each subject
    ought to be "Short Answer" questions is hard-coded into this function.
    Otherwise, all information is read from the yaml configuration.
    """
    for set_config in parsed_sets:

        for set_name, round_num, q_tub in itertools.product(
            set_config.Set, set_config.Rounds, set_config.Template.keys()
        ):

            template = set_config.Template[q_tub]
            difficulties = template.get("LOD")
            subcategories = template.get("Subcategory", [None for e in difficulties])
            q_types = [None for e in difficulties[:-1]] + ["Short Answer"]
            q_letters = [chr(i) for i in range(ord("A"), ord("A") + len(difficulties))]

            if shuffle_config.difficulty:
                shuffle_config.rng.shuffle(difficulties)

            if shuffle_config.subcategory:
                shuffle_config.rng.shuffle(subcategories)

            for lod, subcat, q_type, q_letter in itertools.zip_longest(
                difficulties, subcategories, q_types, q_letters, fillvalue=None
            ):
                yield QuestionDetails(
                    set=set_name,
                    round=f"{set_config.Prefix}{round_num}",
                    tub=q_tub,
                    difficulty=lod,
                    letter=q_letter,
                    qtype=q_type,
                    subcategory=subcat,
                )


def _parse_shuffle(shuffle_config):
    """Helper function that parses the "Shuffle" portion of the
    configuration dictionary."""
    return ShuffleConfig(
        subcategory=shuffle_config["Subcategory"],
        difficulty=shuffle_config["LOD"],
        rng=shuffle_config.get("Seed", None),
    )


def parse_sets(config: List[Dict], round_definitions: Dict) -> List[SetConfig]:
    """Reads a list of set configurations and populates them with the appropriate
    round templates.

    Parameters
    ----------
    config : List[Dict]
        Science Bowl set specifications
    round_definitions : Dict
        Dictionary of Science Bowl round templates

    Returns
    -------
    List[SetConfig]
        List of SetConfig class instances that can be consumed by generate_questions
        to produce question specifications.
    """
    set_configs = deepcopy(config)

    out = []

    for set_config in map(lambda x: SetConfig(**x), set_configs):

        if isinstance(base_template := set_config.Template, str):
            set_config.Template = deepcopy(round_definitions[base_template])

        elif isinstance(set_config.Template, collections.abc.Mapping):
            set_config.Template = _copy_template_and_add(round_definitions, set_config)

        out.append(set_config)

    return out


def _copy_template_and_add(round_definitions: Dict, set_config: Dict) -> Dict:
    """Handles the 'from, add' grammar in the config file.

    Parameters
    ----------
    round_definitions : Dict
        Dictionary of round definition templates.
    set_dict : Dict
        Dictionary describing a set of Science Bowl rounds.

    Returns
    -------
    Dict
        set_dict with the template filled in from round_definitions and
        whichever additions were specified.
    """
    base_template = set_config.Template.get(
        "from",
        KeyError(
            "If Template is a dictionary, it should "
            f"contain a 'from' key, found {set_config.Template.items()}"
        ),
    )

    to_add = set_config.Template.get("add", {})

    template = deepcopy(round_definitions[base_template])
    merge(to_add, template)
    return template


def merge(lhs: Dict, rhs: Dict):
    """Merges left-hand dictionary into right-hand dictionary, combining
    lists of elements if necessary.

    Parameters
    ----------
    lhs, rhs : Dict
        Dicts to be merged. lhs is merged into rhs

    """
    if isinstance(lhs, dict):
        for key, value in lhs.items():
            if key not in rhs:
                rhs[key] = deepcopy(value)
            else:
                merge(value, rhs[key])
    elif isinstance(lhs, list):
        rhs.extend(lhs)
