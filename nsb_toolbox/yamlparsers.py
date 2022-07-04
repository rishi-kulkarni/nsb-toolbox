import collections.abc
import itertools
from copy import deepcopy
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Dict, Generator, List, Optional, Union
from typing_extensions import Self

import numpy as np

from .classes import QuestionType, TossUpBonus
from .importers import load_yaml


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
class Config:
    shuffle_subcategory: bool
    shuffle_pairs: bool
    shuffle_difficulty: bool
    rng: np.random.Generator

    subcat_mismatch_penalty: float
    preferred_writers: List[str]


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


@dataclass(frozen=True)
class ParsedQuestionSpec:
    """Specification that describes the constraints upon each question in each round.

    Attributes
    ----------
    config : ShuffleConfig
        Configuration information
    question_list : List[QuestionDetails]
        Full list of questions. Each of the following properties refers to an array of
        attributes of the QuestionDetail instances in question_list.
    tubs : np.ndarray[str]
    difficulties : np.ndarray[int]
    qtypes : np.ndarray[str]
    subcategories : np.ndarray[str]
    sets : np.ndarray[str]
    rounds : np.ndarray[str]
    qletters : np.ndarray[str]

    Methods
    -------
    from_yaml_dict(yaml_config: Dict)
        Generates a class instance from a dictionary
    from_yaml_path(path: Union[Path, str])
        Generates a class instance from a path to a .yaml file.

    """

    config: Config
    question_list: List[QuestionDetails]

    @cached_property
    def tubs(self) -> np.ndarray:
        return np.array([question.tub.value for question in self.question_list])

    @cached_property
    def difficulties(self) -> np.ndarray:
        return np.array([question.difficulty for question in self.question_list])

    @cached_property
    def qtypes(self) -> np.ndarray:
        return np.array(
            [
                question.qtype.value if question.qtype else ""
                for question in self.question_list
            ]
        )

    @cached_property
    def subcategories(self) -> np.ndarray:
        return np.array(
            [
                question.subcategory if question.subcategory else ""
                for question in self.question_list
            ]
        )

    @cached_property
    def sets(self) -> np.ndarray:
        return np.array([question.set for question in self.question_list])

    @cached_property
    def rounds(self) -> np.ndarray:
        return np.array([question.round for question in self.question_list])

    @cached_property
    def qletters(self) -> np.ndarray:
        return np.array([question.letter for question in self.question_list])

    @classmethod
    def from_yaml_dict(cls, yaml_config: Dict) -> Self:
        """Parses a round specification config and returns an instance of this dataclass.

        Parameters
        ----------
        yaml_config : Dict

        Returns
        -------
        ParsedQuestionSpec
        """
        shuffle_config = _parse_config(yaml_config["Configuration"])
        round_definitions = yaml_config["Round Definitions"]

        parsed_sets = parse_sets(yaml_config["Sets"], round_definitions)

        question_list = list(
            generate_questions(parsed_sets=parsed_sets, config=shuffle_config)
        )

        return cls(config=shuffle_config, question_list=question_list)

    @classmethod
    def from_yaml_path(cls, path: Union[Path, str]) -> Self:
        """Parses a round specification config located at path and returns an instance
        of this dataclass.

        Parameters
        ----------
        path : Union[Path, str]

        Returns
        -------
        ParsedQuestionSpec
        """
        yaml_dict = load_yaml(path=path)
        return cls.from_yaml_dict(yaml_dict)


def generate_questions(
    parsed_sets: Dict, config: Config
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
            q_letters = [chr(i) for i in range(ord("A"), ord("A") + len(difficulties))]

            if config.shuffle_difficulty:
                config.rng.shuffle(difficulties)

            if config.shuffle_pairs:
                config.rng.shuffle(q_letters)

            if config.shuffle_subcategory:
                config.rng.shuffle(subcategories)

            q_types = [None for e in difficulties]
            q_types[np.argmax(q_letters)] = QuestionType.SHORT_ANSWER.value

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


def _parse_config(config: Dict) -> Config:
    """Helper function that parses the "Shuffle" portion of the
    configuration dictionary."""
    return Config(
        shuffle_subcategory=config.get("Shuffle Subcategory", False),
        shuffle_pairs=config.get("Shuffle Pairs", False),
        shuffle_difficulty=config.get("Shuffle LOD", False),
        rng=np.random.default_rng(config.get("Random Seed", None)),
        subcat_mismatch_penalty=config.get("Subcategory Mismatch Penalty", 1.0),
        preferred_writers=config.get("Preferred Writers", [None]),
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
