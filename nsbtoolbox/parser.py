import re

from .sciencebowlquestion import QuestionType, ScienceBowlQuestion, Subject, TossUpBonus

TUB = ("TOSS-UP", "BONUS", "VISUAL BONUS")

SUBJECT_ALIASES = (
    "Life Science",
    "LS",
    "Biology",
    "B",
    "Physical Science",
    "PS",
    "Chemistry",
    "C",
    "Physics",
    "P",
    "Math",
    "M",
    "Earth and Space",
    "ES",
    "Energy",
    "EN",
)

QUESTION_TYPES = ("Multiple Choice", "MC", "Short Answer", "SA")

MC_CHOICES = ("W)", "X)", "Y)", "Z)")


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


