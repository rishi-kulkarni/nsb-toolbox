from email.generator import Generator
import string
from dataclasses import dataclass
from pathlib import Path
from random import shuffle
from typing import Optional, Tuple
from itertools import islice, cycle

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
    """Internal function that combines a base config with a specific
    round config.

    The base config is updated with the round config,
    overwriting any common fields.

    Parameters
    ----------
    round : str
    round_config : dict

    Returns
    -------
    dict

    Raises
    ------
    ValueError
        Raises an error if the resulting config dict is empty. Typically due
        to typos in the config file.
    """
    config = {}

    if "Base" in round_config:
        config.update(round_config["Base"])

    if round in round_config:
        config.update(round_config[round])

    if not config:
        raise ValueError(f"Invalid configuration for round {round}")

    return config


def _generate_questions_per_round(
    round_tuple: Tuple[str, str], config: dict, tub: str
) -> Generator:
    """Takes in a dictionary of configuration information for a round and generates
    QuestionDetail class instances.

    Parameters
    ----------
    round_tuple : Tuple[str, str]
        Tuple in the form of ("Round Type", "Number"), ie ("RR", "1")
    config : dict
        Dict containing configuration information for the round.
    tub : str
        TU or B

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

    # we assume the config file is correct, which allows us to include VB questions in
    # natl finals and have toss-up only TB rounds
    if tub in config:
        difficulties = [
            int(key) for key, value in config[tub].items() for i in range(int(value))
        ]
        shuffle(difficulties)
    else:
        difficulties = []

    # go in reversed order to yield the final question of the round first,
    # which must be short answer
    letters = list(reversed(string.ascii_uppercase))[-len(difficulties) :]

    for idx, v in enumerate(difficulties):
        difficulty = v
        letter = letters[idx]
        if idx == 0:
            qtype = QuestionType("Short Answer")
        else:
            qtype = None
        if subcat_list is not None:
            # this way we can wrap over the subcat list, letting us specify
            # a ratio rather than the exact amount we need
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
    # organizing this generator like this allows us to do lazy evaluation AND yield
    # questions in order from most to least strictness. this makes sure we can
    # populate the final question of each round first, which typically MUST be
    # short answer and might have a subcategory. after doing those, we have
    # more flexibility
    for tub in ("TU", "B", "VB"):
        generators = [
            _generate_questions_per_round(round, config, tub) for round in rounds
        ]
        yield from _roundrobin(*generators)


def _roundrobin(*iterables):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis
    num_active = len(iterables)
    nexts = cycle(iter(it).__next__ for it in iterables)
    while num_active:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            # Remove the iterator we just exhausted from the cycle.
            num_active -= 1
            nexts = cycle(islice(nexts, num_active))
