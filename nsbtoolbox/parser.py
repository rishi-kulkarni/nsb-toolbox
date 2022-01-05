import re
from dataclasses import dataclass
from .sciencebowlquestion import QuestionType, ScienceBowlQuestion, Subject, TossUpBonus

TUB = ("TOSS-UP", "BONUS", "VISUAL BONUS")

SUBJECT_ALIASES = (
    "LIFE",
    "LS",
    "BIOLOGY",
    "B",
    "PHYSICAL",
    "PS",
    "CHEMISTRY",
    "C",
    "PHYSICS",
    "P",
    "MATH",
    "M",
    "EARTH",
    "ES",
    "ENERGY",
    "EN",
)

QUESTION_TYPES = ("Multiple Choice", "MC", "Short Answer", "SA")

MC_CHOICES = ("W)", "X)", "Y)", "Z)")


@dataclass
class Token:
    id: str
    type: str


def lexer(inputstream: list):

    iterator = enumerate(inputstream)

    for idx, word in iterator:

        next_word = peek(inputstream, idx).upper()
        current_word = word.upper()

        if current_word == "ROUND":
            if next_word.isdigit():
                yield Token(int(next_word), "ROUNDNUM")
                next(iterator, None)
            else:
                yield Token(word, "WORD")

        elif current_word in SUBJECT_ALIASES:

            if current_word in ("LIFE", "PHYSICAL", "EARTH"):
                if next_word == "SCIENCE":
                    yield Token(word + " Science", "SUBJECT")
                    next(iterator, None)
                elif (
                    next_word.upper() == "AND"
                    and peek(inputstream, idx, distance=2).upper() == "SPACE"
                ):
                    yield Token("Earth and Space", "SUBJECT")
                    next(iterator, None)
                    next(iterator, None)
            else:
                yield Token(word, "SUBJECT")

        elif current_word == "MULTIPLE" and next_word == "CHOICE":
            yield Token("Multiple Choice", "QTYPE")
            next(iterator, None)
        elif current_word == "SHORT" and next_word == "ANSWER":
            yield Token("Short Answer", "QTYPE")
            next(iterator, None)
        elif current_word in ("MC", "SA"):
            yield Token(word, "QTYPE")

        elif current_word in TUB:
            if next_word == "BONUS":
                yield Token("VISUAL BONUS", "TUB")
                next(iterator)
            else:
                yield Token(word, "TUB")

        elif ")" in current_word:
            if current_word.replace(")", "").isdigit():
                yield Token(word, "NUMID")
            elif current_word in MC_CHOICES:
                yield Token(word, "WXYZ")

        elif current_word == "ANSWER:":
            yield Token(word, "ANSWER")

        else:
            yield Token(word, "WORD")


def peek(inputstream: list, idx: int, distance=1):
    if idx + distance < len(inputstream):
        return inputstream[idx + distance]
    else:
        return ""


def question_parser(input: str):

    question_list = []
    pos = 0

    def question_constructor():
        nonlocal pos
        constructor_dict = {}

        # determine whether a question is a toss-up or a bonus
        tub_finder = re.compile("|".join(TUB))
        tub = tub_finder.match(input[pos:])
        while not tub:
            pos += 1
            tub = tub_finder.match(input[pos:])
        constructor_dict["tu_b"] = TossUpBonus.from_string(tub.group(0))
        pos += tub.end()

        # determine the subject and question question type
        sub_q_finder = re.compile(
            f"({'|'.join(SUBJECT_ALIASES)}) .*({'|'.join(QUESTION_TYPES)})"
        )
        sub_q = sub_q_finder.match(input[pos:])
        while not sub_q:
            pos += 1
            sub_q = sub_q_finder.match(input[pos:])
        constructor_dict["subject"] = Subject.from_string(sub_q.group(1))
        constructor_dict["question_type"] = QuestionType.from_string(sub_q.group(2))
        pos += sub_q.end()

        stem_start = pos

        if constructor_dict["question_type"] is QuestionType.MULTIPLE_CHOICE:
            pass
