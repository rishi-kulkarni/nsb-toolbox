from typing import Generator
import zipfile
import xml.etree.ElementTree
import os
import argparse

WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
PARA = WORD_NAMESPACE + "p"
TEXT = WORD_NAMESPACE + "t"
TABLE = WORD_NAMESPACE + "tbl"
ROW = WORD_NAMESPACE + "tr"
CELL = WORD_NAMESPACE + "tc"


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


def docx_to_stream(path_to_docx: str) -> Generator:
    """Generator that reads a formatted Science Bowl round and yields XML paragraph objects.

    Parameters
    ----------
    path_to_docx : str

    Returns
    -------
    Generator
    """

    with zipfile.ZipFile(path_to_docx) as docx:
        tree = xml.etree.ElementTree.XML(docx.read("word/document.xml"))

    for paragraph in tree.iter(PARA):
        yield "".join(list(paragraph.itertext()))


def text_to_stream(path_to_txt: str) -> Generator:
    """Generator that reads an unformatted Science Bowl text file and yields lines.

    Parameters
    ----------
    path_to_txt : str

    Yields
    -------
    Generator
    """
    with open(path_to_txt) as file:
        for row in file:
            yield row.strip()


if __name__ == "__main__":

    argparser = argparse.ArgumentParser(
        description="Parser for Science Bowl .docx files."
    )
    argparser.add_argument(
        "path",
        metavar="path",
        type=str,
        help="path to the Science Bowl docx file",
    )

    args = argparser.parse_args()

    path_to_data = validate_path(args.path)

    if path_to_data.endswith(".docx"):
        raw_text = docx_to_stream(path_to_data)
    elif path_to_data.endswith(".txt"):
        raw_text = text_to_stream(path_to_data)
