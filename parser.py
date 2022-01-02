from dataclasses import dataclass
from enum import Enum
import docx2txt
import argparse
import os


class TossUpBonus(Enum):
    TOSS_UP = "TOSS-UP"
    BONUS = "BONUS"
    VISUAL_BONUS = "VISUAL BONUS"

    @staticmethod
    def from_string(label):
        """Creates an instance of this class from a string. Provides support
        for aliases.

        Parameters
        ----------
        label : str

        Returns
        -------
        ClassInstance
        """

        _ALIASES = {
            TossUpBonus.TOSS_UP: ("TOSS-UP", "TU"),
            TossUpBonus.BONUS: ("BONUS", "B"),
            TossUpBonus.VISUAL_BONUS: ("VISUAL BONUS", "VB"),
        }
        for enum_type in _ALIASES.keys():
            if label.upper() in _ALIASES[enum_type]:
                return enum_type
        else:
            raise ValueError(f"{label} is not a valid TossUpBonus")


class Subject(Enum):
    LIFE_SCIENCE = "Life Science"
    BIOLOGY = "Biology"
    PHYSICAL_SCIENCE = "Physical Science"
    CHEMISTRY = "Chemistry"
    PHYSICS = "Physics"
    MATH = "Math"
    ESSC = "Earth and Space"
    ENERGY = "Energy"

    @staticmethod
    def from_string(label: str):
        """Creates an instance of this class from a string. Provides support
        for aliases.

        Parameters
        ----------
        label : str

        Returns
        -------
        ClassInstance
        """
        _ALIASES = {
            Subject.LIFE_SCIENCE: ("LIFE SCIENCE", "LS"),
            Subject.BIOLOGY: ("BIOLOGY", "B"),
            Subject.PHYSICAL_SCIENCE: ("PHYSICAL SCIENCE", "PS"),
            Subject.CHEMISTRY: ("CHEMISTRY", "C"),
            Subject.PHYSICS: ("PHYSICS", "P"),
            Subject.MATH: ("MATH", "M"),
            Subject.ESSC: ("EARTH AND SPACE", "ES"),
            Subject.ENERGY: ("ENERGY", "EN"),
        }
        for enum_type in _ALIASES.keys():
            if label.upper() in _ALIASES[enum_type]:
                return enum_type
        else:
            raise ValueError(f"{label} is not a valid Subject")


class QuestionType(Enum):
    MULTIPLE_CHOICE = "MULTIPLE CHOICE"
    SHORT_ANSWER = "SHORT ANSWER"

    @staticmethod
    def from_string(label):
        """Creates an instance of this class from a string. Provides support
        for aliases.

        Parameters
        ----------
        label : str

        Returns
        -------
        ClassInstance
        """
        _ALIASES = {
            QuestionType.MULTIPLE_CHOICE: ("MULTIPLE CHOICE", "MC"),
            QuestionType.SHORT_ANSWER: ("SHORT ANSWER", "SA"),
        }
        for enum_type in _ALIASES.keys():
            if label.upper() in _ALIASES[enum_type]:
                return enum_type
        else:
            raise ValueError(f"{label} is not a valid Subject")


@dataclass
class ScienceBowlQuestion:
    """Class containing all fields describing a Science Bowl question."""

    tu_b: TossUpBonus
    subject: Subject
    question_type: QuestionType
    stem: str
    choices: list[str]
    answer: str

    question_set: str = "N/A"
    round: str = "N/A"
    q_letter: str = "N/A"

    source: str = "Unknown"
    author: str = "Unknown"
    comments: str = ""
    ID: int = 0

    def __post_init__(self):
        if not isinstance(self.tu_b, TossUpBonus):
            self.tu_b = TossUpBonus.from_string(self.tu_b)

        if not isinstance(self.subject, Subject):
            self.subject = Subject.from_string(self.subject)

        if not isinstance(self.question_type, QuestionType):
            self.question_type = QuestionType.from_string(self.question_type)


def validate_path(path_string: str) -> str:
    """Validates that incoming path exists.

    Parameters
    ----------
    path_string : str

    Returns
    -------
    path_string

    Raises
    ------
    FileNotFoundError

    """
    if os.path.exists(path_string):
        return path_string
    else:
        raise FileNotFoundError(f"No such file: {path_string}")


if __name__ == "__main__":

    argparser = argparse.ArgumentParser(
        description="Parser for Science Bowl .docx files."
    )
    argparser.add_argument(
        "path", metavar="path", type=str, help="path to the Science Bowl docx file"
    )

    args = argparser.parse_args()

    path_to_data = validate_path(args.path)

    raw_text = docx2txt.process(path_to_data).split()
