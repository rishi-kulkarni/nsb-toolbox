from enum import Enum


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
            "tu": TossUpBonus.TOSS_UP,
            "toss-up": TossUpBonus.TOSS_UP,
            "b": TossUpBonus.BONUS,
            "bonus": TossUpBonus.BONUS,
            "vb": TossUpBonus.VISUAL_BONUS,
            "visual bonus": TossUpBonus.VISUAL_BONUS,
        }
        try:
            return _ALIASES[label.lower()]
        except KeyError:
            return TossUpBonus(label)


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
    MULTIPLE_CHOICE = "Multiple Choice"
    SHORT_ANSWER = "Short Answer"

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
            if label.upper() in (x.upper() for x in _ALIASES[enum_type]):
                return enum_type
        else:
            raise ValueError(f"{label} is not a valid Subject")


class ErrorLogger:
    def __init__(self, verbosity):
        self.verbosity = verbosity
        self.errors = []
        self.row_number = None

        self.stats = {
            "TOSS-UP": 0,
            "BONUS": 0,
            "Short Answer": 0,
            "Multiple Choice": 0,
        }

    def set_row(self, row_number):
        self.row_number = row_number

    def log_error(self, error_msg: str):
        self.errors.append(f"Question {self.row_number}: {error_msg}")

    def __repr__(self) -> str:
        ret = None
        if self.verbosity is True:
            ret = "\n".join(self.errors)
        else:
            ret = f"Found {len(self.errors)} errors."

        stats = [f"{key}: {item}" for key, item in self.stats.items()]
        stats_table = (
            "\n\n"
            + "Question Statistics\n"
            + "-------------------\n"
            + "\n".join(stats)
        )
        ret += stats_table
        return ret
