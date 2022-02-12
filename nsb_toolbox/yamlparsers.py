from email.generator import Generator
import string
from dataclasses import dataclass
from pathlib import Path
from random import shuffle
from typing import Optional, Tuple

import strictyaml

from .classes import QuestionType, TossUpBonus


@dataclass
class QuestionDetails:
    round: str
    tub: TossUpBonus
    difficulty: int
    letter: str
    qtype: Optional[QuestionType] = None
    subcategory: Optional[str] = None


def load_yaml(path: Path) -> strictyaml.YAML:
    """Parses a yaml files and returns a YAML representation object.

    Parameters
    ----------
    path : Path

    Returns
    -------
    strictyaml.YAML

    Raises
    ------
    FileNotFoundError
    """
    if path.exists():
        with open(path) as file:
            data = file.read()
            data = strictyaml.load(data)
            return data.data
    else:
        raise FileNotFoundError(f"no such file: {path}")


def _prepare_round_config(round: str, round_config: dict) -> dict:
    config = {}

    if "Base" in round_config:
        config.update(round_config["Base"])

    if round in round_config:
        config.update(round_config[round])

    if "TU" not in config or "B" not in config:
        raise ValueError(f"No tossup or bonus numbers specified for {round}")

    return config


def _generate_questions_per_round(
    round_tuple: Tuple[str, str], config: dict
) -> Generator:
    """Takes in a dictionary of configuration information for a round and generates
    QuestionDetail class instances.

    Parameters
    ----------
    round_tuple : Tuple[str, str]
        Tuple in the form of ("Round Type", "Number"), ie ("RR", "1")
    config : dict
        Dict containing configuration information for the round.

    Yields
    -------
    Generator
        Yields QuestionDetails objects
    """
    round = "".join(round_tuple)
    round_config = config[round_tuple[0]]

    config = _prepare_round_config(round, round_config)

    # this makes subcategories go from {'Space': 2, 'Earth': 1} to
    # ['Space', 'Space', 'Earth']
    if "Subcategories" in config:
        subcat_list = [
            key
            for key, value in config["Subcategories"].items()
            for i in range(int(value))
        ]
    else:
        subcat_list = None

    for tub in ("TU", "B", "VB"):
        if tub in config:
            difficulties = [
                int(key)
                for key, value in config[tub].items()
                for i in range(int(value))
            ]
            shuffle(difficulties)
        else:
            difficulties = []

        letters = list(reversed(string.ascii_uppercase))[-len(difficulties) :]

        for idx, v in enumerate(difficulties):
            difficulty = v
            letter = letters[idx]
            if idx == 0:
                qtype = QuestionType("Short Answer")
            else:
                qtype = None
            if subcat_list is not None:
                subcategory = subcat_list[idx % len(subcat_list)]
            else:
                subcategory = None

            yield QuestionDetails(
                round=round,
                tub=TossUpBonus.from_string(tub),
                difficulty=difficulty,
                letter=letter,
                qtype=qtype,
                subcategory=subcategory,
            )


def generate_questions_per_set(config: dict) -> Generator:
    """Generator that yields QuestionDetails objects for every
    question specified in an assignment yaml file.

    Parameters
    ----------
    config : dict
        Configuration dictionary pulled from a yaml file

    Yields
    -------
    Generator
        Yields QuestionDetails objects
    """
    rounds = [
        (key, str(idx + 1))
        for key, value in config["Rounds"].items()
        for idx in range(int(value))
    ]
    for round in rounds:
        yield from _generate_questions_per_round(round, config)
