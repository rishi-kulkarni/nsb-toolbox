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


def docx_to_txt_stream(path_to_docx: str) -> list:
    """Generator that reads a formatted Science Bowl round and yields XML paragraph objects.

    Parameters
    ----------
    path_to_docx : str

    Returns
    -------
    list
        List of words in the target docx.
    """

    with zipfile.ZipFile(path_to_docx) as docx:
        tree = xml.etree.ElementTree.XML(docx.read("word/document.xml"))

    for paragraph in tree.iter(PARA):
        yield "".join(list(paragraph.itertext()))


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

    raw_text = docx_to_txt_stream(path_to_data)
