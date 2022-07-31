import logging

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


class RowContextFilter(logging.Filter):

    curr_row = None
    _num_records = 0

    def filter(self, record: logging.LogRecord) -> bool:
        self._num_records += 1
        record.row = self.curr_row
        return True


class FormatErrorsFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "Row: %(row)-8s %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
