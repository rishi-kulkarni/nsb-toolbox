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


def parser(inputstream):
    """Generator that yields ScienceBowlQuestion class instances.

    Parameters
    ----------
    inputstream : list of str
        List of strings representing words in a Science Bowl file.

    Yields
    -------
    ScienceBowlQuestion instances

    Raises
    ------
    ValueError
        Upon reaching an unexpected token.
    """
    lexer_obj = lexer(inputstream)

    context = "PRE-Q"
    choice_context = 0

    scibowlq_fields = {}
    stem = []
    choices = []
    current_choice = []
    answer = []

    for token in lexer_obj:

        if context == "PRE-Q":

            if token.type == "ROUNDNUM":
                scibowlq_fields["round"] = token.id

            elif token.type == "TUB":
                scibowlq_fields["tu_b"] = token.id
                context = "PRE-SUBJ"

            else:
                raise ValueError(
                    f"Invalid token type. Expected ROUNDNUM or TUB, got {token.type}"
                )

        elif context == "PRE-SUBJ":

            if token.type == "NUMID":
                scibowlq_fields["q_letter"] = int(token.id.replace(")", ""))

            elif token.type == "SUBJECT":
                scibowlq_fields["subject"] = token.id
                context = "PRE-TYPE"

            else:
                raise ValueError(
                    f"Invalid token type. Expected NUMID OR SUBJECT, got {token.type}"
                )

        elif context == "PRE-TYPE":

            if token.type == "QTYPE":
                scibowlq_fields["question_type"] = token.id
                context = "STEM"

            elif token.type == "WORD":
                continue

            else:
                raise ValueError(
                    f"Invalid token type. Expected QTYPE or WORD, got {token.type}"
                )

        elif context == "STEM":

            if token.type in ("NUMID", "WXYZ"):
                scibowlq_fields["stem"] = " ".join(stem)
                context = "CHOICES"
                choice_context = token.id

            elif token.type == "ANSWER":
                scibowlq_fields["choices"] = []
                scibowlq_fields["stem"] = " ".join(stem)
                context = "ANSWER"

            else:
                stem.append(token.id)

        elif context == "CHOICES":

            if (token.type in ("NUMID", "WXYZ")) and check_choice_context(
                choice_context, token.id
            ):
                choices.append(" ".join(current_choice))
                current_choice.clear()
                choice_context = token.id

            elif token.type == "ANSWER":
                choices.append(" ".join(current_choice))
                current_choice.clear()
                scibowlq_fields["choices"] = choices
                context = "ANSWER"

            else:
                current_choice.append(token.id)

        elif context == "ANSWER":

            if token.type in ("ROUNDNUM", "TUB"):

                scibowlq_fields["answer"] = " ".join(answer)

                yield ScienceBowlQuestion(**scibowlq_fields)

                answer.clear()
                stem.clear()
                choices.clear()
                choice_context = 0
                scibowlq_fields.clear()

                if token.type == "ROUNDNUM":
                    scibowlq_fields["round"] = token.id
                    context = "PRE-Q"

                elif token.type == "TUB":
                    scibowlq_fields["tu_b"] = token.id
                    context = "PRE-SUBJ"

            elif not any(char.isalnum() for char in token.id):
                continue

            else:
                answer.append(token.id)

    scibowlq_fields["answer"] = " ".join(answer)

    yield ScienceBowlQuestion(**scibowlq_fields)


def check_choice_context(context: str, token_id: str):
    """Given that we are parsing a question that has choices, checks that a given NUMID
    or WXYZ token is indicating the next choice. This avoids problems with questions
    that include coordinate pairs.

    Parameters
    ----------
    context : str
    token_id : str

    Returns
    -------
    bool

    """
    if context in MC_CHOICES:
        return token_id == MC_CHOICES[MC_CHOICES.index(context) + 1]
    elif context.replace(")", "").isdigit():
        return int(token_id.replace(")", "")) == int(context.replace(")", "")) + 1
    else:
        raise ValueError(f"Invalid context: {context}")


def lexer(inputstream: list):
    """Performs lexical analysis on a stream of input words.

    Parameters
    ----------
    inputstream : list
        List of strings representing words in a Science Bowl file.

    Yields
    -------
    generator object
        Token generator
    """
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
            else:
                yield Token(word, "WORD")

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
