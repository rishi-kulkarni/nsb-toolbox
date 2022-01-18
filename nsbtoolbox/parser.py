from dataclasses import dataclass
from typing import Generator
from .classes import ScienceBowlQuestion
import string

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

METADATA_FIELDS = ("SET:", "SOURCE:", "LOD:", "ROUND:", "QLETTER:", "AUTHOR:")


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
    lexer_obj = tokenizer(inputstream)

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
    elif context.strip(string.punctuation).isdigit():
        return (
            int(token_id.strip(string.punctuation))
            == int(context.strip(string.punctuation)) + 1
        )
    else:
        raise ValueError(f"Invalid context: {context}")


def emit(current_token_list: list, ID: str) -> Token:
    """Emits a token and clears the stack.

    Parameters
    ----------
    current_token : list
    ID : str

    Returns
    -------
    Token
    """
    ret = Token(" ".join(current_token_list), ID)
    current_token_list.clear()
    return ret


def tokenizer(inputstream: Generator):
    """Performs lexical analysis on a stream of input words.

    Parameters
    ----------
    inputstream : Generator
        Yields lines of text from a Science Bowl file.

    Yields
    -------
    generator object
        Token generator
    """
    current_token = []
    context = "START"

    for row in inputstream:

        if row == "":
            row = "<BLANKLINE>"

        for word in row.split():

            current_token.append(word)

            if context == "START":

                if word.upper() in ("TOSS-UP", "BONUS") and len(current_token) == 1:
                    yield emit(current_token, "TUB")

                elif word.upper() == "ROUND" and len(current_token) == 1:
                    continue

                elif word.strip(string.punctuation).isdigit():
                    if current_token[0].upper() == "ROUND":
                        yield emit(current_token, "ROUNDNUM")
                    elif len(current_token) == 1:
                        yield emit(current_token, "QNUM")

                elif word.upper() in SUBJECT_ALIASES and len(current_token) == 1:
                    if word.upper() in ("LIFE", "PHYSICAL", "EARTH"):
                        continue
                    else:
                        yield emit(current_token, "SUBJECT")

                elif word.upper() == "SCIENCE" and current_token[0].upper() in (
                    "LIFE",
                    "PHYSICAL",
                ):
                    yield emit(current_token, "SUBJECT")

                elif word.upper() == "AND" and current_token[0].upper() == "EARTH":
                    continue

                elif (
                    word.upper() == "SPACE"
                    and " ".join(current_token).upper() == "EARTH AND SPACE"
                ):
                    yield emit(current_token, "SUBJECT")

                elif word.upper() in ("MC", "SA") and len(current_token) == 1:
                    yield emit(current_token, "QTYPE")
                    context = "STEM"

                elif word.upper() in ("MULTIPLE", "SHORT") and len(current_token) == 1:
                    continue

                elif word.upper() in ("CHOICE", "ANSWER") and current_token[
                    0
                ].upper() in ("MULTIPLE", "SHORT"):
                    yield emit(current_token, "QTYPE")
                    context = "STEM"

                elif word.upper() == "<BLANKLINE>":
                    current_token.pop()

                elif word.upper() in METADATA_FIELDS:
                    current_token.clear()
                    context = "METADATA"
                    current_token.append(word)

                else:
                    current_token.pop()

            elif context == "STEM":

                if word.upper() == "<BLANKLINE>":
                    current_token.pop()

                elif word.upper() == "W)":
                    current_token.pop()
                    yield emit(current_token, "STEM")
                    context = "CHOICES"
                    choice_context = word.upper()

                elif (
                    any(p in word.upper() for p in string.punctuation)
                    and word.strip(string.punctuation) == "1"
                ):
                    current_token.pop()
                    yield emit(current_token, "STEM")
                    context = "CHOICES"
                    choice_context = word.upper()

                elif word.upper() == "ANSWER:":
                    current_token.pop()
                    yield emit(current_token, "STEM")
                    context = "ANSWER"

                else:
                    continue

            elif context == "CHOICES":

                if word.upper() in MC_CHOICES:
                    if check_choice_context(choice_context, word.upper()):
                        current_token.pop()
                        current_token[-1] = current_token[-1].rstrip(",.;")
                        yield emit(current_token, "CHOICE")
                        choice_context = word.upper()
                    else:
                        continue

                elif (
                    any(p in word.upper() for p in string.punctuation)
                    and word.strip(string.punctuation).isdigit()
                ):
                    if check_choice_context(choice_context, word.upper()):
                        current_token.pop()
                        current_token[-1] = current_token[-1].rstrip(",.;")
                        yield emit(current_token, "CHOICE")
                        choice_context = word.upper()
                    else:
                        continue

                elif word.upper() in ("ANSWER", "<BLANKLINE>"):
                    current_token.pop()
                    current_token[-1] = current_token[-1].rstrip(",.;")
                    context = "ANSWER"
                    yield emit(current_token, "CHOICE")

                else:
                    continue

            elif context == "ANSWER":

                if word.upper() in METADATA_FIELDS:
                    context = "METADATA"
                    current_token.pop()
                    yield emit(current_token, "ANSWER")
                    current_token.append(word)

                elif word.upper() == "<BLANKLINE>":
                    current_token.pop()
                    context = "START"
                    yield emit(current_token, "ANSWER")

                elif word.upper() == "ANSWER:":
                    current_token.pop()

                else:
                    continue

            elif context == "METADATA":

                if word.upper() in METADATA_FIELDS and len(current_token) > 1:
                    current_token.pop()
                    yield emit(
                        current_token[1:],
                        current_token[0].strip(string.punctuation).upper(),
                    )
                    current_token.clear()
                    current_token.append(word)

                elif word.upper() == "<BLANKLINE>":
                    current_token.pop()
                    context = "START"
                    yield emit(
                        current_token[1:],
                        current_token[0].strip(string.punctuation).upper(),
                    )
                    current_token.clear()

                else:
                    continue

    if context == "ANSWER" and len(current_token) > 0:
        yield emit(current_token, "ANSWER")
    elif context == "METADATA" and len(current_token) > 0:
        yield emit(
            current_token[1:],
            current_token[0].strip(string.punctuation).upper(),
        )
